import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from core.config import config
from core.prompts import BACKEND_SYSTEM
from core.utils import get_logger, parse_llm_json, format_file_summary
from agents.state import AppState

logger = get_logger("backend")

llm = ChatOpenAI(
    model=config.codegen_model,
    temperature=config.temperature,
    openai_api_key=config.openai_api_key,
    max_retries=config.max_retries
)


def backend_agent(state: AppState) -> AppState:
    logger.info("Backend agent started")
    client_id = state.get("client_id")

    if state.get("error"):
        logger.warning("Skipping — previous agent failed")
        return {}

    if client_id:
        from api.websocket import stream_agent_start
        asyncio.run(stream_agent_start(client_id, "backend"))

    try:
        plan = state['plan']
        api_contracts = plan.get('api_contracts', [])

        messages = [
            SystemMessage(content=BACKEND_SYSTEM),
            HumanMessage(content=(
                f"Generate backend code for this app.\n\n"
                f"Plan: {plan}\n\n"
                f"API Contracts to implement:\n"
                f"{chr(10).join(['  ' + r['method'] + ' ' + r['path'] for r in state.get('backend_routes', [])])}\n\n"
                f"Generate ONLY:\n"
                f"- backend/src/models/[AppSpecificModel].js (NOT User.js — that's a template)\n"
                f"- backend/src/routes/index.js (Express Router mounted at /api)\n\n"
                f"Templates already handle: server.js, auth.js middleware, User.js, errorHandler.js, routes/auth.js\n"
                f"Do NOT regenerate those files."
            ))
        ]

        response = llm.invoke(messages)
        backend_code = parse_llm_json(response.content, "backend")

        if not backend_code:
            raise ValueError("Backend agent returned invalid JSON")

        # Extract actual routes from generated index.js for frontend to use
        routes_summary = _extract_routes(backend_code)

        logger.info(f"Backend complete:\n{format_file_summary(backend_code)}")
        logger.info(f"Routes extracted: {routes_summary}")

        if client_id:
            from api.websocket import stream_agent_complete
            asyncio.run(stream_agent_complete(client_id, "backend", list(backend_code.keys())))

        return {
            "backend_code": backend_code,
            "backend_routes": routes_summary
        }

    except Exception as e:
        logger.error(f"Backend agent failed: {e}")
        if client_id:
            from api.websocket import stream_agent_error
            asyncio.run(stream_agent_error(client_id, "backend", str(e)))
        return {"error": f"Backend failed: {str(e)}"}


def _extract_routes(backend_code: dict) -> list:
    """Extract route definitions from generated backend code."""
    import re
    routes = []

    for path, content in backend_code.items():
        if "routes/index.js" in path or "routes/tasks" in path:
            # Find route definitions: router.get('/tasks', ...)
            matches = re.findall(
                r"router\.(get|post|put|patch|delete)\(['\"]([^'\"]+)['\"]",
                content
            )
            for method, route_path in matches:
                routes.append({
                    "method": method.upper(),
                    "path": f"/api{route_path}" if not route_path.startswith("/api") else route_path
                })

    return routes