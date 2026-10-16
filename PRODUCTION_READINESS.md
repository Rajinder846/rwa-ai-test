# Production-readiness plan

## Release decision

The current workflow has a sound safety direction: an LLM interprets requests,
while deterministic code routes actions and an investment requires explicit user
confirmation. It is suitable for development and controlled demonstrations, but
must not execute real investments until every **P0** item below is complete and
tested.

## Target transaction flow

```text
Authenticated request
  -> validate JWT and resolve user identity
  -> verify conversation belongs to that user
  -> classify intent (LLM, structured output)
  -> validate action-specific input (Pydantic)
  -> retrieve current quote/eligibility from backend
  -> persist a short-lived confirmation record
  -> user confirms once
  -> atomically claim confirmation + execute with idempotency key
  -> backend revalidates and records transaction
  -> return an auditable result
```

The RWA backend is the source of truth for authorization, KYC/AML/suitability,
wallet/payment authorization, price, availability, limits, and the final
investment record. The AI service must never be the only enforcement point.

## P0 — required before real-money use

### 1. Implement authentication and authorization

**Where:** `app/auth/dependencies.py`, `app/api/dependencies/auth.py`,
`app/auth/models.py`, and the API gateway/deployment configuration.

**Current state:** `get_auth_context` accepts a bearer token without validating
it and assigns every request `"temporary-user-id"`.

**Change:**

- Validate issuer, audience, signature, expiry, and not-before claims against
  the identity provider's JWKS.
- Resolve `user_id` only from validated immutable claims (`sub` or equivalent).
- Enforce scopes/roles for every domain action; do not treat token presence as
  authorization.
- Reject missing, malformed, expired, or insufficiently scoped tokens with 401
  or 403, without exposing token or claim content.
- Have the RWA backend independently validate the forwarded token or use a
  narrowly scoped service-to-service credential with an actor/user assertion.

**Done when:** integration tests prove that forged, expired, and wrong-audience
tokens fail; two valid users cannot access each other's thread or results.

### 2. Replace in-memory graph state with durable, isolated persistence

**Where:** `app/graph/graph.py`, `app/core/redis.py`, `app/main.py`, and a new
checkpoint/confirmation persistence module.

**Current state:** the graph uses `MemorySaver()`. Its confirmation state is
lost on restart and is not shared across containers. Redis is connected but is
not the graph checkpointer.

**Change:**

- Use a production LangGraph checkpointer backed by Postgres or Redis as
  appropriate for the selected LangGraph version. Prefer Postgres for durable,
  auditable records; Redis can support short-lived coordination.
- Namespace checkpoint keys by validated user ID and conversation ID. Do not
  use a raw client-supplied conversation ID as the sole key.
- Add retention/expiry for chat content and pending confirmations, and encrypt
  data at rest where required.
- Store a separate confirmation record containing user ID, quote/version,
  payload digest, creation/expiry time, status, and one-time nonce.

**Done when:** an interrupted confirmation survives a service restart, works
across replicas, expires safely, and cannot be resumed by another user.

### 3. Make execution idempotent and race-safe

**Where:** `app/graph/nodes/investment_node.py`,
`app/graph/nodes/execute_investment_node.py`,
`app/api_clients/rwa_api_client.py`, and the RWA backend's investment endpoint.

**Current state:** confirmation is state-based and the `POST /investor/invest`
request has no visible idempotency key. Repeated requests or uncertain network
outcomes can lead to duplicate execution.

**Change:**

- Create a server-generated `confirmation_id` and an opaque one-time resume
  token; never let the client provide transaction payload fields at resume.
- Atomically transition `pending -> executing` with compare-and-set semantics.
  Return the prior completed result for later attempts.
- Send a stable idempotency key (for example `confirmation_id`) to the backend
  and require the backend to persist and enforce it.
- Treat timeouts after submission as `unknown/pending reconciliation`, not as
  a failed transaction. Query the backend by idempotency key before retrying.
- Clear or mark a confirmation consumed only after its final durable outcome is
  recorded.

**Done when:** concurrent confirm calls and retry-after-timeout tests result in
exactly one backend investment and one audit record.

### 4. Revalidate financial controls at the authoritative boundary

**Where:** RWA backend investment/quote services; retain defensive checks in
`app/graph/nodes/investment_node.py`.

**Change:**

- Generate a backend quote with asset version, price, currency, quantity,
  fees, expiry, and a quote ID; show that exact quote to the user.
- At execution, revalidate asset status, price/quote expiry, availability,
  KYC/AML/sanctions status, investor suitability, jurisdiction, limits,
  balance/payment authorization, and wallet ownership.
- Make payment method a validated user/backend-selected value; do not hard-code
  `CRYPTO_WALLET` in the AI service.
- Use decimal-safe contracts end-to-end; reject invalid/negative/non-finite
  amounts and define quantity precision in the backend contract.

**Done when:** changing the price, asset availability, user eligibility, or
payment authorization after confirmation causes a safe rejection/re-quote.

### 5. Bind conversations and resumes to ownership

**Where:** `app/api/chat.py` and the durable conversation store.

**Change:**

- Create conversation IDs server-side, or verify each supplied ID belongs to
  `auth.user.user_id` before `graph.ainvoke` or `Command(resume=...)`.
- Bind the pending confirmation to user, conversation, action, and payload
  digest. Require the same authenticated principal at resume.
- Add request IDs and idempotency keys to API contracts; validate request size,
  message length, and allowed content types.

**Done when:** cross-user conversation and confirmation-resume attempts return
403 and produce a security audit event.

## P1 — required for a reliable production service

### Input contracts and LLM boundary

**Where:** `app/agents/schemas.py`, `app/agents/supervisor.py`,
`app/graph/router.py`, and each workflow.

- Replace the free-form `action: str` and `parameters: dict[str, Any]` with
  action-specific discriminated Pydantic models.
- Validate after LLM output and again immediately before a backend call. Reject
  unknown fields and enforce ID formats, amount bounds, currencies, pagination,
  and enums.
- Keep the action allowlist in one typed registry rather than duplicating it
  between prompt and router.
- Handle LLM timeouts, malformed structured output, provider safety blocks,
  and rate limits as controlled errors. Set a low deterministic temperature for
  classification.
- Apply prompt-injection defenses: backend data is untrusted reference data,
  not instructions; use output/content limits and never expose secrets in
  prompts, logs, or responses.

### HTTP client reliability

**Where:** `app/api_clients/rwa_api_client.py`.

- Use an application-lifespan shared `httpx.AsyncClient` with connection limits,
  explicit connect/read/write/pool timeouts, and graceful shutdown.
- Define retries only for safe idempotent reads. For writes, rely on the
  idempotency protocol and reconcile uncertain outcomes.
- Map backend 401/403/404/409/422/429/5xx errors to stable public codes; log
  safe diagnostic details internally.
- Validate backend response schemas rather than assuming response envelopes.

### Observability, audit, and operations

**Where:** `app/main.py`, `app/core/logger.py`, `app/core/exception_handlers.py`,
`app/api/health.py`, deployment manifests, and monitoring configuration.

- Emit structured logs and OpenTelemetry traces with request, conversation,
  confirmation, backend correlation, and idempotency IDs. Redact JWTs, PII,
  financial identifiers, and prompt content by default.
- Publish metrics for latency, error rate, LLM failures/cost, confirmation
  abandonment, transaction outcomes, duplicate suppression, and dependency
  health.
- Split liveness from readiness. Readiness should fail when required persistent
  storage is unavailable; health endpoints must not write to Redis or use
  `print`.
- Add rate limiting, request-body limits, CORS policy, TLS termination,
  secret rotation, dependency/image scanning, backups, alerts, runbooks, and
  a rollback plan.

### API completeness and user experience

**Where:** `app/workflows.py`, `app/api/chat.py`, and frontend/API contracts.

- Return typed API response models, proper HTTP status codes, and machine
  readable error codes.
- Implement backend support before advertising portfolio, loan, payout-claim,
  staking, sell, or unstake actions. The current structured
  `ACTION_NOT_AVAILABLE` behavior is safe, but the supervisor should avoid
  suggesting unavailable features.
- Present an investment confirmation with quote expiry, fees, payment method,
  risks/disclosures, and a clear cancellation path.

## P2 — quality and scale improvements

**Where:** CI/CD configuration (not yet present), `Dockerfile`,
`docker-compose.yml`, tests, and documentation.

- Add database migrations, infrastructure-as-code, environment separation, and
  least-privilege service accounts.
- Pin dependencies with a lockfile, generate an SBOM, scan dependencies and
  containers, and run as a non-root user (the current Dockerfile already does
  the latter).
- Add autoscaling/load testing and failure drills for LLM, Redis/Postgres, and
  backend outages.
- Establish data classification, retention/deletion workflows, access reviews,
  audit-log retention, and required legal/compliance controls for the operating
  jurisdiction.

## Test plan and release gates

**Where:** expand `app/tests/`; add contract, integration, and end-to-end test
suites in CI. The current suite contains useful unit tests, but several legacy
files are skipped and there are no production boundary tests.

Required automated tests:

1. JWT signature/claims/scope validation and user-to-thread authorization.
2. Durable checkpoint recovery across restart and across two service instances.
3. Confirmation expiry, cancellation, duplicate click, concurrent resume, and
   timeout reconciliation; verify exactly-once backend execution.
4. Backend API contract tests for every request and response envelope.
5. Financial edge cases: stale quote, price change, depleted tokens, decimal
   precision, limits, KYC/suitability changes, and payment rejection.
6. LLM malformed-output, unavailable-provider, prompt-injection, and oversized
   input tests; the LLM must never bypass the deterministic action boundary.
7. Load, rate-limit, dependency-outage, logging-redaction, and security scans.

**Production launch gate:** security review, threat model, backend idempotency
verification, operational runbook/on-call readiness, disaster-recovery test,
and approval by the product, security, compliance, and backend owners.
