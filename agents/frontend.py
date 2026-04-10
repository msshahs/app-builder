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


def _get_resource_info(plan: dict) -> dict:
    """Derive the primary resource name from the plan's API contracts."""
    contracts = plan.get("api_contracts", [])
    for c in contracts:
        path = c.get("path", "")
        if path.startswith("/api/"):
            parts = path.split("/")
            if len(parts) >= 3:
                resource = parts[2]  # e.g. "products" from /api/products
                # Skip parameterized segments
                if resource and not resource.startswith("{") and not resource.startswith(":"):
                    resource_singular = resource.rstrip("s") if resource.endswith("s") else resource
                    Resource = resource_singular.capitalize()
                    # Find the response shape for the list endpoint
                    response_key = resource  # default
                    return {
                        "resource": resource,          # "products"
                        "resource_singular": resource_singular,  # "product"
                        "Resource": Resource,           # "Product"
                        "hook": f"use{resource.capitalize()}",   # "useProducts"
                        "setter": f"set{resource.capitalize()}",  # "setProducts"
                        "fetch_fn": f"fetch{resource.capitalize()}",  # "fetchProducts"
                        "add_fn": f"add{Resource}",     # "addProduct"
                        "update_fn": f"update{Resource}",  # "updateProduct"
                        "delete_fn": f"delete{Resource}",  # "deleteProduct"
                        "response_key": response_key,   # "products"
                    }

    # Fallback — should rarely happen if planner works correctly
    logger.warning("Could not derive resource name from api_contracts — using generic 'items'")
    return {
        "resource": "items",
        "resource_singular": "item",
        "Resource": "Item",
        "hook": "useItems",
        "setter": "setItems",
        "fetch_fn": "fetchItems",
        "add_fn": "addItem",
        "update_fn": "updateItem",
        "delete_fn": "deleteItem",
        "response_key": "items",
    }


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
        plan = state["plan"]
        backend_routes = state.get("backend_routes", [])
        api_contracts = plan.get("api_contracts", [])
        design = plan.get("design", {})

        # Derive resource info from the plan
        ri = _get_resource_info(plan)
        logger.info(f"Resource info: {ri['resource']} → hook: {ri['hook']}, setter: {ri['setter']}")

        # Build routes context — prefer actual extracted routes, fall back to contracts
        if backend_routes:
            routes_context = "ACTUAL BACKEND ROUTES (use these exact paths):\n"
            for r in backend_routes:
                routes_context += f"  {r['method']} {r['path']}\n"
        else:
            routes_context = "API CONTRACTS (use these paths):\n"
            for c in api_contracts:
                routes_context += f"  {c['method']} {c['path']} → {c.get('response_shape', '')}\n"

        # Build component specs context
        component_specs = plan.get("component_specs", [])
        specs_context = "COMPONENT SPECS:\n"
        for spec in component_specs:
            specs_context += f"  {spec['name']}: {spec.get('description', '')}\n"
            if spec.get("api_calls"):
                specs_context += f"    API calls: {', '.join(spec['api_calls'])}\n"

        # Build frontend routes
        frontend_routes_text = "\n".join([
            f"  {r['path']} → {r.get('component', r.get('redirect', ''))}"
            for r in plan.get("frontend_routes", [])
        ])

        # Files to generate
        files_to_generate = [f for f in plan.get("file_structure", []) if f.startswith("frontend/")]

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
                f"  Primary shade: {design.get('primary_shade', '600')}\n"
                f"  Background: {design.get('background', 'gray-50')}\n"
                f"  Card background: {design.get('card_background', 'white')}\n"
                f"  Card style: {design.get('card_style', 'shadow-sm rounded-xl')}\n"
                f"  Dark mode: {design.get('dark_mode', False)}\n"
                f"  Style: {design.get('style', 'minimal')}\n"
                f"  Mood: {design.get('mood', 'Clean and modern')}\n\n"
                f"PRIMARY RESOURCE (use these EXACT names throughout all files):\n"
                f"  Plural (state variable): {ri['resource']}  e.g. const [{ri['resource']}, {ri['setter']}] = useState([])\n"
                f"  Singular: {ri['resource_singular']}\n"
                f"  Hook name: {ri['hook']}  e.g. import {{ {ri['hook']} }} from '../hooks/{ri['hook']}'\n"
                f"  State setter: {ri['setter']}\n"
                f"  Fetch function: {ri['fetch_fn']}\n"
                f"  CRUD functions: {ri['add_fn']}, {ri['update_fn']}, {ri['delete_fn']}\n"
                f"  Response key: {ri['response_key']}  e.g. data.{ri['response_key']} from API\n\n"
                f"{routes_context}\n\n"
                f"{specs_context}\n\n"
                f"Frontend routes to implement:\n{frontend_routes_text}\n\n"
                f"Files to generate:\n"
                + "\n".join(f"  {f}" for f in files_to_generate) + "\n\n"
                f"WIRING RULES (apply exactly):\n"
                f"- App.jsx: import {{ getToken }} from './utils/tokenStorage', use PrivateRoute with getToken()\n"
                f"- LoginPage: useNavigate, redirect to /dashboard after login(email, password)\n"
                f"- RegisterPage: name + email + password fields, register(name, email, password), redirect after\n"
                f"- Hook '{ri['hook']}': wrap {ri['fetch_fn']} in useCallback, call in useEffect([{ri['fetch_fn']}])\n"
                f"  return {{ {ri['resource']}, {ri['fetch_fn']}, {ri['add_fn']}, {ri['update_fn']}, {ri['delete_fn']}, loading, error }}\n"
                f"  Handle response: Array.isArray(data) ? data : data.{ri['response_key']} || data.items || []\n"
                f"- Dashboard: const {{ {ri['resource']}, {ri['add_fn']}, {ri['update_fn']}, {ri['delete_fn']}, loading }} = {ri['hook']}()\n"
                f"  Pass onSubmit AND onClose to form modal\n"
                f"  handleAdd = async (data) => {{ await {ri['add_fn']}(data); setIsModalOpen(false); }}\n"
                f"  Use item._id not item.id (MongoDB uses _id)\n"
                f"- Form components: accept onSubmit + onClose, call both on submit, Cancel calls onClose\n"
                f"- All /api/ routes: api.get('/api/{ri['resource']}') not api.get('/{ri['resource']}')\n\n"
                f"Generate complete, beautiful, production-ready code. No TODOs."
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

        return {
            "frontend_code": frontend_code,
            "resource_info": ri,
        }

    except Exception as e:
        logger.error(f"Frontend agent failed: {e}")
        if client_id:
            from api.websocket import stream_agent_error
            asyncio.run(stream_agent_error(client_id, "frontend", str(e)))
        return {"error": f"Frontend failed: {str(e)}"}
