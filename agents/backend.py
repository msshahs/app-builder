import asyncio
import re
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
        plan = state["plan"]
        api_contracts = plan.get("api_contracts", [])

        # Format API contracts clearly for the LLM
        contracts_text = "\n".join([
            f"  {c['method']} {c['path']} → {c.get('response_shape', '')}"
            for c in api_contracts
        ])

        # Identify app-specific models (exclude auth-related)
        models = plan.get("components", {}).get("backend", {}).get("models", [])
        app_models = [m for m in models if m.lower() not in ("user",)]

        messages = [
            SystemMessage(content=BACKEND_SYSTEM),
            HumanMessage(content=(
                f"Generate backend code for this app.\n\n"
                f"App name: {plan.get('app_name')}\n"
                f"Description: {plan.get('description')}\n\n"
                f"API Contracts to implement:\n{contracts_text}\n\n"
                f"App-specific models to create: {app_models}\n"
                f"(Do NOT create User.js — it's already in templates)\n\n"
                f"Generate:\n"
                f"- backend/src/models/[EachAppModel].js (one file per model)\n"
                f"- backend/src/routes/index.js (Express Router implementing all /api/* routes)\n\n"
                f"Templates already handle: server.js, auth.js middleware, User.js, errorHandler.js, routes/auth.js\n"
                f"Do NOT regenerate those files.\n\n"
                f"The routes/index.js router will be mounted at /api by server.js.\n"
                f"So a route defined as router.get('/products', ...) is accessible at /api/products."
            ))
        ]

        response = llm.invoke(messages)
        backend_code = parse_llm_json(response.content, "backend")

        if not backend_code:
            raise ValueError("Backend agent returned invalid JSON")

        # Extract actual routes from generated code
        routes_summary = _extract_routes(backend_code)
        # Also include auth routes from contracts for frontend reference
        auth_routes = [
            {"method": c["method"], "path": c["path"]}
            for c in api_contracts
            if c["path"].startswith("/auth/")
        ]

        logger.info(f"Backend complete:\n{format_file_summary(backend_code)}")
        logger.info(f"Routes extracted: {routes_summary}")

        if client_id:
            from api.websocket import stream_agent_complete
            asyncio.run(stream_agent_complete(client_id, "backend", list(backend_code.keys())))

        return {
            "backend_code": backend_code,
            "backend_routes": routes_summary + auth_routes,
            "api_contracts": api_contracts,
        }

    except Exception as e:
        logger.error(f"Backend agent failed: {e}")
        if client_id:
            from api.websocket import stream_agent_error
            asyncio.run(stream_agent_error(client_id, "backend", str(e)))
        return {"error": f"Backend failed: {str(e)}"}


def _extract_routes(backend_code: dict) -> list:
    """Extract route definitions from generated backend code."""
    routes = []

    for path, content in backend_code.items():
        # Match any routes/*.js file (not just tasks)
        if "routes/" in path and path.endswith(".js") and "auth" not in path:
            matches = re.findall(
                r"router\.(get|post|put|patch|delete)\(['\"]([^'\"]+)['\"]",
                content
            )
            for method, route_path in matches:
                # Normalize: routes/index.js routes are mounted at /api
                normalized = route_path if route_path.startswith("/api") else f"/api{route_path}"
                routes.append({
                    "method": method.upper(),
                    "path": normalized
                })

    return routes
