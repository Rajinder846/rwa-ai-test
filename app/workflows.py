"""Deterministic domain workflows and deterministic API response formatting."""
from __future__ import annotations

import calendar
import re
import time
from typing import Any

import httpx
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from app.api_clients.rwa_api_client import RWAAPIClient
from app.core.llm import get_llm
from app.core.logger import get_logger
from app.graph.state import WorkflowState

logger = get_logger("workflows")


def _client(config: RunnableConfig) -> RWAAPIClient:
    token = config.get("configurable", {}).get("user_jwt")
    if not token:
        raise ValueError("Investor authentication token is missing.")
    return RWAAPIClient(token)


def _ok(data: Any) -> dict:
    return {"success": True, "error_code": None, "data": data, "message": None}


def _error(code: str, message: str) -> dict:
    return {"success": False, "error_code": code, "data": None, "message": message}


def _message_text(content: Any) -> str:
    """Normalize provider message content without exposing provider metadata."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [
            str(item.get("text", ""))
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        ]
        if parts:
            return "\n".join(parts)
    return str(content)


async def _call(name: str, state: WorkflowState, callback) -> dict:
    started = time.perf_counter()
    try:
        result = await callback()
        logger.info("workflow_api_call", request_id=state.get("request_id"), user_id=state.get("user_id"), workflow=state.get("domain"), action=state.get("action"), api=name, elapsed_ms=round((time.perf_counter() - started) * 1000, 2))
        return _ok(result)
    except ValueError as exc:
        return _error("AUTHENTICATION_REQUIRED", str(exc))
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        return _error("BACKEND_REQUEST_FAILED", f"The backend rejected this request (HTTP {status}).")
    except httpx.HTTPError:
        return _error("BACKEND_UNAVAILABLE", "The backend service is currently unavailable. Please try again.")
    except Exception:
        logger.exception("workflow_failed", request_id=state.get("request_id"), user_id=state.get("user_id"), workflow=state.get("domain"), action=state.get("action"))
        return _error("INTERNAL_ERROR", "The request could not be completed.")


async def asset_workflow(state: WorkflowState, config: RunnableConfig) -> dict:
    p, action = state.get("parameters", {}), state.get("action")
    try:
        client = _client(config)
        if action in {"list_assets", "search_assets"}:
            result = await _call("search_assets", state, lambda: client.search_assets(search=str(p.get("search") or p.get("asset_name") or ""), status=str(p.get("status") or "")))
        elif action in {"get_asset", "get_asset_details"} and p.get("asset_id"):
            result = await _call("get_asset", state, lambda: client.get_asset(str(p["asset_id"])))
        else:
            result = _error("MISSING_PARAMETER", "Please provide the asset ID or a search term.")
    except ValueError as exc:
        result = _error("AUTHENTICATION_REQUIRED", str(exc))
    return {"tool_result": result, "final_result": result, "status": "completed" if result["success"] else "failed"}


async def payout_workflow(state: WorkflowState, config: RunnableConfig) -> dict:
    action = state.get("action")
    try:
        client = _client(config)
    except ValueError as exc:
        result = _error("AUTHENTICATION_REQUIRED", str(exc))
        return {"tool_result": result, "final_result": result, "status": "failed"}
    tab = "history" if action in {"get_payout_history", "get_payouts"} else "upcoming"
    if action == "claim_payout":
        result = _error("ACTION_NOT_AVAILABLE", "Payout claiming is not yet exposed by the backend API.")
    else:
        result = await _call("get_payouts", state, lambda: client.get_payouts(tab=tab))
    return {"tool_result": result, "final_result": result, "status": "completed" if result["success"] else "failed"}


async def staking_workflow(state: WorkflowState, config: RunnableConfig) -> dict:
    action, p = state.get("action"), state.get("parameters", {})
    try:
        client = _client(config)
    except ValueError as exc:
        result = _error("AUTHENTICATION_REQUIRED", str(exc))
        return {"tool_result": result, "final_result": result, "status": "failed"}
    if action in {"get_staking_positions", "get_staking_history", "get_staking_rewards"}:
        result = await _call("get_my_stakings", state, lambda: client.get_my_stakings(status=str(p.get("status", ""))))
    elif action == "list_staking_pools":
        category_id = str(p.get("category_id") or "")
        if not category_id:
            categories_result = await _call("get_asset_categories", state, client.get_asset_categories)
            if not categories_result["success"]:
                result = categories_result
            else:
                names = _category_names(categories_result["data"])
                message = f"Please specify a category. Available categories: {', '.join(names)}." if names else "Please specify a staking pool category."
                result = _error("CATEGORY_SELECTION_REQUIRED", message)
        else:
            result = await _call("get_staking_pools", state, lambda: client.get_staking_pools(category_id=category_id))
    else:
        result = _error("ACTION_NOT_AVAILABLE", f"{action} is not yet exposed by the backend API.")
    return {"tool_result": result, "final_result": result, "status": "completed" if result["success"] else "failed"}


async def portfolio_workflow(state: WorkflowState, config: RunnableConfig) -> dict:
    # Do not fabricate portfolio information while the corresponding backend endpoint is absent.
    return {"tool_result": _error("ACTION_NOT_AVAILABLE", "Portfolio retrieval is not yet exposed by the backend API."), "final_result": _error("ACTION_NOT_AVAILABLE", "Portfolio retrieval is not yet exposed by the backend API."), "status": "failed"}


async def loan_workflow(state: WorkflowState, config: RunnableConfig) -> dict:
    return {"tool_result": _error("ACTION_NOT_AVAILABLE", "Loan operations are not yet exposed by the backend API."), "final_result": _error("ACTION_NOT_AVAILABLE", "Loan operations are not yet exposed by the backend API."), "status": "failed"}


async def clarification_node(_: WorkflowState) -> dict:
    result = _error("UNSUPPORTED_ACTION", "I couldn't map that request to a supported platform action. Please rephrase it.")
    return {"tool_result": result, "final_result": result, "status": "failed"}


async def reasoning_agent(state: WorkflowState, config: RunnableConfig) -> dict:
    """The only specialized node allowed a second LLM call; it is read-only."""
    try:
        client = _client(config)
    except ValueError as exc:
        result = _error("AUTHENTICATION_REQUIRED", str(exc))
        return {"tool_result": result, "final_result": result, "status": "failed"}
    assets = await _call("search_assets", state, lambda: client.search_assets())
    if not assets["success"]:
        return {"tool_result": assets, "final_result": assets, "status": "failed"}
    prompt = "You are a read-only RWA investment analyst. Use only the supplied backend data. Do not claim to execute transactions, determine eligibility, or invent missing data. Give a concise analysis and state uncertainty."
    answer = await get_llm().ainvoke([SystemMessage(content=prompt), HumanMessage(content=f"Request: {state.get('user_message')}\nAvailable assets: {assets['data']}")])
    result = _ok({"analysis": _message_text(answer.content), "sources": ["available_assets"]})
    return {"tool_result": assets, "final_result": result, "status": "completed"}


ERROR_RESPONSES = {
    "KYC_NOT_COMPLETED": "KYC verification is required before investing.",
    "ASSET_NOT_FOUND": "The requested asset was not found.",
    "INSUFFICIENT_BALANCE": "Your available balance is insufficient.",
    "INSUFFICIENT_TOKENS": "There are not enough tokens available.",
    "INVESTMENT_LIMIT_EXCEEDED": "This investment exceeds your allowed limit.",
    "PAYMENT_FAILED": "The payment could not be completed.",
    "TRANSACTION_FAILED": "The transaction could not be completed.",
}


def _extract_records(data: Any) -> list[dict[str, Any]]:
    """Extract a record collection without assuming one backend response envelope."""
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if not isinstance(data, dict):
        return []

    for key in ("assets", "items", "results", "records", "payouts", "stakings", "stakes", "pools", "positions"):
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    if "data" in data:
        nested = _extract_records(data["data"])
        if nested:
            return nested
    # Last resort: the first list-of-objects value under any key, so an
    # unanticipated envelope name still surfaces real data instead of "none found".
    for value in data.values():
        if isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
            return value
    return []


def _asset_label(asset: dict[str, Any]) -> str:
    basic_info = asset.get("basicInfo") if isinstance(asset.get("basicInfo"), dict) else {}
    return str(basic_info.get("assetName") or asset.get("assetName") or asset.get("name") or asset.get("title") or "Unnamed asset")


def _format_asset_list(data: Any) -> str:
    assets = _extract_records(data)
    if not assets:
        return "No available assets were found."

    lines = ["Available assets:", ""]
    for asset in assets:
        basic_info = asset.get("basicInfo") if isinstance(asset.get("basicInfo"), dict) else {}
        details = [f"**{_asset_label(asset)}**"]
        location = basic_info.get("location") or basic_info.get("city") or asset.get("location")
        status = asset.get("status") or basic_info.get("status")
        asset_id = asset.get("_id") or asset.get("id") or asset.get("assetId")
        if location:
            details.append(str(location))
        if status:
            details.append(f"Status: {status}")
        if asset_id:
            details.append(f"ID: {asset_id}")
        lines.append(f"- {' — '.join(details)}")
    return "\n".join(lines)


def _asset_detail(data: Any) -> dict[str, Any] | None:
    """Unwrap the common API envelopes used by the asset-detail endpoint."""
    if not isinstance(data, dict):
        return None
    value = data.get("data", data)
    if isinstance(value, dict) and isinstance(value.get("asset"), dict):
        value = value["asset"]
    return value if isinstance(value, dict) else None


def _first_value(*values: Any) -> Any:
    return next((value for value in values if value not in (None, "", [], {})), None)


def _category_names(data: Any) -> list[str]:
    records = _extract_records(data)
    names = [_first_value(item.get("name"), item.get("categoryName"), item.get("title")) for item in records]
    return [str(name) for name in names if name]


def _detail_line(label: str, value: Any) -> str | None:
    return f"- **{label}:** {value}" if value not in (None, "", [], {}) else None


def _format_asset_details(data: Any) -> str:
    asset = _asset_detail(data)
    if not asset:
        return "No asset details were returned by the backend."

    basic = asset.get("basicInfo") if isinstance(asset.get("basicInfo"), dict) else {}
    financial = asset.get("financialDetails") if isinstance(asset.get("financialDetails"), dict) else {}
    token = asset.get("tokenEconomics") if isinstance(asset.get("tokenEconomics"), dict) else {}
    progress = asset.get("investmentProgress") if isinstance(asset.get("investmentProgress"), dict) else {}
    lines = [f"## {_asset_label(asset)}", ""]

    overview = [
        _detail_line("Asset ID", _first_value(asset.get("_id"), asset.get("id"), asset.get("assetId"))),
        _detail_line("Status", _first_value(asset.get("status"), basic.get("status"))),
        _detail_line("Type", _first_value(basic.get("assetType"), basic.get("type"), asset.get("assetType"), asset.get("type"))),
        _detail_line("Location", _first_value(basic.get("location"), basic.get("city"), asset.get("location"))),
    ]
    overview = [line for line in overview if line]
    if overview:
        lines.extend(["### Overview", *overview])

    investment = [
        _detail_line("Minimum investment", _first_value(financial.get("minimumInvestment"), asset.get("minimumInvestment"))),
        _detail_line("Expected ROI", _first_value(financial.get("expectedROI"), financial.get("expectedRoi"), asset.get("expectedROI"))),
        _detail_line("Annual yield", _first_value(financial.get("annualYield"), financial.get("expectedYield"), asset.get("yield"))),
        _detail_line("Token price", _first_value(token.get("tokenPriceSAR"), token.get("tokenPrice"), token.get("tokenPriceUSD"))),
        _detail_line("Available tokens", _first_value(progress.get("tokensAvailable"), token.get("availableTokens"), asset.get("tokensAvailable"))),
    ]
    investment = [line for line in investment if line]
    if investment:
        lines.extend(["", "### Investment", *investment])

    description = _first_value(basic.get("description"), asset.get("description"))
    if description:
        lines.extend(["", "### Description", str(description)])
    return "\n".join(lines)


def _total_count(data: Any) -> int | None:
    """Look for a pagination total without assuming one backend envelope."""
    candidates = [data]
    if isinstance(data, dict) and isinstance(data.get("data"), dict):
        candidates.append(data["data"])
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        for key in ("total", "totalRecords", "totalCount", "count"):
            value = candidate.get(key)
            if isinstance(value, int):
                return value
    return None


_NOISE_KEYS = {"__v", "password", "token"}


def _humanize_key(key: str) -> str:
    """Turn a camelCase or snake_case field name into a readable label."""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", key).replace("_", " ")
    return spaced.strip().title()


def _flatten_record(prefix: str, value: Any, out: dict[str, Any], depth: int = 0, max_depth: int = 2) -> None:
    """Flatten a record's fields into label paths, without assuming any specific schema."""
    if isinstance(value, dict):
        if depth >= max_depth:
            return
        for key, nested in value.items():
            if key.startswith("_") and key != "_id" or key.lower() in _NOISE_KEYS:
                continue
            _flatten_record(f"{prefix}.{key}" if prefix else key, nested, out, depth + 1, max_depth)
        return
    if isinstance(value, list):
        scalars = [str(v) for v in value if isinstance(v, (str, int, float, bool))]
        if scalars:
            out[prefix] = ", ".join(scalars)
        if depth < max_depth:
            for index, item in enumerate(v for v in value if isinstance(v, dict)):
                _flatten_record(f"{prefix}[{index}]", item, out, depth + 1, max_depth)
        return
    if value not in (None, "", [], {}):
        out[prefix] = value


def _format_record_line(record: dict[str, Any]) -> str:
    flat: dict[str, Any] = {}
    for key, value in record.items():
        if key.lower() in _NOISE_KEYS:
            continue
        _flatten_record(key, value, flat)
    parts = [f"{_humanize_key(path)}: {value}" for path, value in flat.items()]
    return " — ".join(parts) if parts else "(no details available)"


def _month_label(value: Any) -> str:
    match = re.fullmatch(r"(\d{4})-(\d{1,2})", str(value))
    if not match:
        return str(value)
    year, month = int(match.group(1)), int(match.group(2))
    if not 1 <= month <= 12:
        return str(value)
    return f"{calendar.month_name[month]} {year}"


def _record_asset_name(item: dict[str, Any]) -> str | None:
    asset = item.get("asset") if isinstance(item.get("asset"), dict) else {}
    basic = asset.get("basicInfo") if isinstance(asset.get("basicInfo"), dict) else {}
    return _first_value(item.get("assetName"), basic.get("assetName"), asset.get("name"), asset.get("assetName"))


def _format_payouts(action: str, data: Any) -> str:
    tab = "history" if action in {"get_payout_history", "get_payouts"} else "upcoming"

    # Known shape: {"data": {"history": {"items": [...], "pagination": {...}},
    # "upcoming": {...}, "trend": [...], "overview": {...}}}. `trend` is a
    # monthly total across all assets and has no per-asset breakdown, so it
    # must not be used here even though it also looks like a record list.
    payload = data.get("data") if isinstance(data, dict) else None
    section = payload.get(tab) if isinstance(payload, dict) else None
    items = section.get("items") if isinstance(section, dict) else None
    if not isinstance(items, list):
        items = _extract_records(data)  # unrecognized shape: fall back rather than assume no data

    if not items:
        return "No payouts were found." if tab == "history" else "No upcoming payouts were found."

    lines = ["Payouts:" if tab == "history" else "Upcoming payouts:", ""]
    for item in items:
        if not isinstance(item, dict):
            continue
        asset_name = _record_asset_name(item)
        period = _first_value(item.get("period"), _month_label(item["month"]) if isinstance(item.get("month"), str) else None, item.get("date"))
        amount = item.get("amount")
        currency = _first_value(item.get("currency"), "SAR")
        status = item.get("status")

        if period is None and amount is None and not asset_name:
            lines.append(f"- {_format_record_line(item)}")
            continue

        label = str(period) if period else "Payout"
        if asset_name:
            label = f"{label} — {asset_name}"
        text = f"- {label}: {amount} {currency}" if amount is not None else f"- {label}"
        if status:
            text += f" ({status})"
        lines.append(text)

    total = section.get("pagination", {}).get("total") if isinstance(section, dict) and isinstance(section.get("pagination"), dict) else _total_count(data)
    if isinstance(total, int):
        lines.extend(["", f"Total records: {total}"])
    return "\n".join(lines)


def _format_stakings(data: Any) -> str:
    items = _extract_records(data)
    if not items:
        return "No staking positions were found."

    lines = ["Staking positions:", ""]
    for item in items:
        if not isinstance(item, dict):
            continue
        pool = item.get("poolId") if isinstance(item.get("poolId"), dict) else {}
        pool_asset = pool.get("assetId") if isinstance(pool.get("assetId"), dict) else {}
        pool_name = _first_value(pool.get("poolName"), pool.get("name"))
        category = _first_value(pool.get("category"), pool_asset.get("category"))
        staked = item.get("stakedAmount")
        reward = item.get("rewardAmount")
        status = item.get("status")
        annual_yield = pool.get("annualYield")
        progress = item.get("lockPeriodProgress")
        unlock_in = item.get("unlockIn")

        if pool_name is None and staked is None:
            lines.append(f"- {_format_record_line(item)}")
            continue

        label = f"{pool_name} ({category})" if pool_name and category else str(pool_name or "Staking position")
        details = [label]
        if staked is not None:
            details.append(f"Staked: {staked}")
        if annual_yield is not None:
            details.append(f"APY: {annual_yield}%")
        if reward is not None:
            details.append(f"Reward: {reward}")
        if status:
            details.append(f"Status: {status}")
        if status == "active" and isinstance(progress, (int, float)):
            unlock_text = f", unlocks in {unlock_in} days" if unlock_in is not None else ""
            details.append(f"Lock progress: {progress}%{unlock_text}")
        lines.append(f"- {' — '.join(details)}")

    return "\n".join(lines)


def _format_staking_pools(data: Any) -> str:
    items = _extract_records(data)
    if not items:
        return "No staking pools were found."

    lines = ["Staking pools:", ""]
    for item in items:
        if not isinstance(item, dict):
            continue
        name = _first_value(item.get("poolName"), item.get("name"))
        category = item.get("category")
        apy = item.get("annualYield")
        lock_period = item.get("lockPeriod")
        min_stake = item.get("minStake")
        total_staked = item.get("totalStaked")
        target = item.get("targetStakeAmount")
        participants = item.get("participantsCount")
        status = item.get("status")

        if name is None:
            lines.append(f"- {_format_record_line(item)}")
            continue

        details = [str(name)]
        if category:
            details.append(str(category))
        if apy is not None:
            details.append(f"APY: {apy}%")
        if lock_period is not None:
            details.append(f"Lock period: {lock_period} days")
        if min_stake is not None:
            details.append(f"Min stake: {min_stake}")
        if total_staked is not None and target is not None:
            details.append(f"Staked: {total_staked}/{target}")
        if participants is not None:
            details.append(f"Participants: {participants}")
        if status:
            details.append(f"Status: {status}")
        lines.append(f"- {' — '.join(details)}")

    return "\n".join(lines)


def _format_success(action: str, data: Any) -> str:
    if action == "invest" and isinstance(data, dict):
        return data.get("message") or "Your investment was completed successfully."
    if action in {"list_assets", "search_assets"}:
        return _format_asset_list(data)
    if action in {"get_asset", "get_asset_details"}:
        return _format_asset_details(data)
    if action.startswith("get_payout"):
        return _format_payouts(action, data)
    if action == "list_staking_pools":
        return _format_staking_pools(data)
    if action.startswith("get_staking"):
        return _format_stakings(data)
    return "Your request was completed successfully."


async def response_formatter(state: WorkflowState) -> dict:
    result = state.get("final_result") or state.get("tool_result") or _error("INTERNAL_ERROR", "The request did not return a result.")
    if result.get("success"):
        data = result.get("data")
        response = data.get("analysis") if state.get("domain") == "reasoning" and isinstance(data, dict) else _format_success(state.get("action", ""), data)
    else:
        response = ERROR_RESPONSES.get(result.get("error_code"), result.get("message", "The request could not be completed."))
    return {"response": response, "messages": [AIMessage(content=response)], "status": "completed" if result.get("success") else "failed"}
