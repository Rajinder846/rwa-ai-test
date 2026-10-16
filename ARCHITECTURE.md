# Hybrid workflow architecture

## Previous architecture

The graph routed from a supervisor LLM to a domain agent LLM. Asset, investment,
payout, and staking agents then selected tools through another LLM call; portfolio
and loan agents generated answers from conversation history. This added LLM calls
to ordinary retrieval and allowed conversational components to influence the
execution path.

## Current architecture

`START -> supervisor -> deterministic router -> domain workflow/reasoning agent
-> response formatter -> END`.

The supervisor returns a Pydantic `SupervisorDecision` containing a domain,
high-level action, parameters, and reasoning flag. The router validates that the
action belongs to the declared domain and selects a graph node without an LLM.
Normal workflows directly invoke backend API clients and return the common
`success/error_code/data/message` result. The formatter converts that result to a
response without calling an LLM.

The reasoning node is the sole second-LLM path. It receives only read-only data
and has no transaction capability. Investments remain deterministic and pause for
explicit confirmation before the transaction endpoint is called.

## File-level changes

- `app/agents/schemas.py`: structured supervisor contract.
- `app/agents/supervisor.py`: high-level intent/action extraction only.
- `app/graph/router.py`: action registry and deterministic routing.
- `app/graph/graph.py`: conditional workflow graph.
- `app/workflows.py`: asset, portfolio, payout, loan, staking, reasoning, error,
  and response-formatting behavior.
- `app/graph/nodes/investment_node.py`: deterministic investment preparation and
  confirmation.
- `app/graph/nodes/execute_investment_node.py`: confirmed transaction execution.
- `app/tests/test_hybrid_architecture.py`: routing, workflow, confirmation, and
  formatter contract tests.

## Migration notes

Existing asset, payout, staking, and investment API clients are reused. This
repository currently has no portfolio or loan client endpoint, nor endpoints for
staking mutations or payout claims. Those actions deliberately return structured
`ACTION_NOT_AVAILABLE` errors until backend services are supplied; they never fall
back to an LLM. Add each new client method, map the action in its workflow, and add
a mocked workflow test when its backend endpoint becomes available.
