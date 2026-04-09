import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from core.config import config
from core.prompts import FRONTEND_SYSTEM
from core.utils import get_logger, parse_llm_json, format_file_summary
from agents.state import AppState

logger = get_logger("frontend")

llm = ChatOpenAI(
    model=config.codegen_model,
    temperature=config.temperature,
    openai_api_key=config.openai_api_key,
    max_retries=config.max_retries
)


def frontend_agent(state: AppState) -> AppState:
    logger.info("Frontend agent started")
    client_id = state.get("client_id")

    if state.get("error"):
        logger.warning("Skipping — previous agent failed")
        return {}

    if client_id:
        from api.websocket import stream_agent_start
        asyncio.run(stream_agent_start(client_id, "frontend"))

    try:
        plan = state['plan']
        backend_routes = state.get("backend_routes", [])
        api_contracts = plan.get("api_contracts", [])
        design = plan.get("design", {})

        # Build routes context for frontend
        routes_context = ""
        if backend_routes:
            routes_context = "ACTUAL BACKEND ROUTES (use these exact paths):\n"
            for r in backend_routes:
                routes_context += f"  {r['method']} {r['path']}\n"
        elif api_contracts:
            routes_context = "API CONTRACTS:\n"
            for c in api_contracts:
                routes_context += f"  {c['method']} {c['path']} → {c.get('response_shape', '')}\n"

        # Build component specs context
        component_specs = plan.get("component_specs", [])
        specs_context = ""
        if component_specs:
            specs_context = "COMPONENT SPECS:\n"
            for spec in component_specs:
                specs_context += f"  {spec['name']}: {spec['description']}\n"
                if spec.get("api_calls"):
                    specs_context += f"    API calls: {', '.join(spec['api_calls'])}\n"

        messages = [
            SystemMessage(content=FRONTEND_SYSTEM),
            HumanMessage(content=(
                f"Generate ALL frontend files for this app.\n\n"
                f"CRITICAL PATH RULE: Every file path MUST start with 'frontend/src/'\n"
                f"WRONG: src/App.jsx — CORRECT: frontend/src/App.jsx\n\n"
                f"App: {plan.get('app_name')}\n"
                f"Description: {plan.get('description')}\n\n"
                f"Design:\n"
                f"  Primary color: {design.get('primary_color', 'violet')}\n"
                f"  Background: {design.get('background', 'gray-50')}\n"
                f"  Dark mode: {design.get('dark_mode', False)}\n"
                f"  Style: {design.get('style', 'minimal')}\n"
                f"  Mood: {design.get('mood', 'Clean and modern')}\n"
                f"  Card background: {design.get('card_background', 'white')}\n\n"
                f"{routes_context}\n\n"
                f"{specs_context}\n\n"
                f"Frontend routes to generate:\n"
                f"{chr(10).join(['  ' + r['path'] + ' → ' + r.get('component', '') for r in plan.get('frontend_routes', [])])}\n\n"
                f"Files to generate:\n"
                f"{chr(10).join([f for f in plan['file_structure'] if f.startswith('frontend/')])}\n\n"
                f"Full plan: {plan}\n\n"
                f"REMEMBER ALL WIRING RULES:\n"
                f"- App.jsx uses getToken() not isAuthenticated\n"
                f"- LoginPage and RegisterPage use useNavigate + redirect after success\n"
                f"- RegisterPage has name field, calls register(name, email, password)\n"
                f"- Hooks wrap fetch in useCallback, export fetchX function\n"
                f"- Dashboard passes onSubmit AND onClose to form modals\n"
                f"- Dashboard implements handleAdd: async (data) => {{ await addTask(data); setOpen(false); }}\n"
                f"- Form components call onSubmit(data) then onClose()\n"
                f"- Cards use item._id not item.id\n"
                f"- All API calls use /api/ prefix\n\n"
                f"Generate complete, beautiful, production-ready code."
            ))
        ]

        response = llm.invoke(messages)
        frontend_code = parse_llm_json(response.content, "frontend")

        if not frontend_code:
            raise ValueError("Frontend agent returned invalid JSON")

        logger.info(f"Frontend complete:\n{format_file_summary(frontend_code)}")

        if client_id:
            from api.websocket import stream_agent_complete
            asyncio.run(stream_agent_complete(client_id, "frontend", list(frontend_code.keys())))

        return {"frontend_code": frontend_code}

    except Exception as e:
        logger.error(f"Frontend agent failed: {e}")
        if client_id:
            from api.websocket import stream_agent_error
            asyncio.run(stream_agent_error(client_id, "frontend", str(e)))
        return {"error": f"Frontend failed: {str(e)}"}