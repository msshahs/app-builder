import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from core.config import config
from core.utils import get_logger, parse_llm_json
from core.prompts import REVIEW_SYSTEM
from agents.state import AppState

logger = get_logger("review")

llm = ChatOpenAI(
    model=config.review_model,
    temperature=0,
    openai_api_key=config.openai_api_key,
    max_retries=config.max_retries
)


def review_agent(state: AppState) -> AppState:
    attempts = state.get("review_attempts", 0) + 1
    logger.info(f"Review agent started (attempt {attempts})")
    client_id = state.get("client_id")

    if state.get("error"):
        logger.warning("Skipping — previous agent failed")
        return {}

    if client_id:
        from api.websocket import stream_agent_start
        asyncio.run(stream_agent_start(client_id, "review"))

    try:
        frontend_code = state.get("frontend_code") or {}
        backend_routes = state.get("backend_routes", [])
        resource_info = state.get("resource_info", {})
        plan = state.get("plan", {})

        if not frontend_code:
            logger.warning("No frontend code — skipping review")
            return {
                "review_result": {"passed": True, "issues": [], "summary": "No frontend code to review"},
                "review_attempts": attempts,
                "current_stage": "review_complete"
            }

        # Concat all frontend files for review
        frontend_files = "\n\n".join([
            f"=== {path} ===\n{content}"
            for path, content in frontend_code.items()
        ])

        routes_context = "\n".join([
            f"  {r['method']} {r['path']}" for r in backend_routes
        ]) if backend_routes else "No routes extracted"

        # Resource-specific wiring context for reviewer
        ri = resource_info
        resource_context = ""
        if ri:
            resource_context = (
                f"\nRESOURCE NAMING (check these exact names are used):\n"
                f"  Hook: {ri.get('hook', 'useItems')}\n"
                f"  State variable: {ri.get('resource', 'items')}\n"
                f"  Fetch function: {ri.get('fetch_fn', 'fetchItems')}\n"
                f"  Add function: {ri.get('add_fn', 'addItem')}\n"
                f"  API path: /api/{ri.get('resource', 'items')}\n"
            )

        messages = [
            SystemMessage(content=REVIEW_SYSTEM),
            HumanMessage(content=(
                f"Review this React frontend for wiring issues.\n\n"
                f"App: {plan.get('app_name', 'App')}\n"
                f"Description: {plan.get('description', '')}\n"
                f"{resource_context}\n"
                f"Available backend routes:\n{routes_context}\n\n"
                f"Frontend files:\n{frontend_files}"
            ))
        ]

        response = llm.invoke(messages)
        review_result = parse_llm_json(response.content, "review")

        if not review_result:
            raise ValueError("Review agent returned invalid JSON")

        critical_issues = [
            i for i in review_result.get("issues", [])
            if i.get("severity") == "critical"
        ]

        if review_result.get("passed"):
            logger.info("Review passed")
        else:
            logger.warning(
                f"Review found {len(review_result['issues'])} issues "
                f"({len(critical_issues)} critical)"
            )
            for issue in review_result["issues"]:
                logger.warning(f"  [{issue['severity'].upper()}] {issue['file']}: {issue['issue']}")

        if client_id:
            from api.websocket import stream_review_result
            asyncio.run(stream_review_result(
                client_id,
                review_result.get("passed", False),
                review_result.get("issues", [])
            ))

        return {
            "review_result": review_result,
            "review_attempts": attempts,
            "current_stage": "review_complete"
        }

    except Exception as e:
        logger.error(f"Review agent failed: {e}")
        if client_id:
            from api.websocket import stream_agent_error
            asyncio.run(stream_agent_error(client_id, "review", str(e)))
        return {"error": f"Review failed: {str(e)}"}
