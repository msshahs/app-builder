import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from core.config import config
from core.prompts import PLANNER_SYSTEM
from core.utils import get_logger, parse_llm_json
from agents.state import AppState

logger = get_logger("planner")

llm = ChatOpenAI(
    model=config.planner_model,
    temperature=config.temperature,
    openai_api_key=config.openai_api_key,
    max_retries=config.max_retries
)


def planner_agent(state: AppState) -> AppState:
    logger.info("Planner agent started")
    client_id = state.get("client_id")

    # Stream start event
    if client_id:
        from api.websocket import stream_agent_start
        asyncio.run(stream_agent_start(client_id, "planner"))

    try:
        messages = [
            SystemMessage(content=PLANNER_SYSTEM),
            HumanMessage(content=f"Create a detailed technical plan for: {state['user_prompt']}")
        ]

        response = llm.invoke(messages)
        plan = parse_llm_json(response.content, "planner")

        if not plan:
            raise ValueError("Planner returned invalid JSON")

        required_keys = ["app_name", "components", "file_structure"]
        missing = [k for k in required_keys if k not in plan]
        if missing:
            raise ValueError(f"Plan missing required keys: {missing}")

        logger.info(f"Plan ready — app: {plan['app_name']}")

        # Stream complete event
        if client_id:
            from api.websocket import stream_agent_complete
            asyncio.run(stream_agent_complete(
                client_id, "planner",
                [plan["app_name"]]
            ))

        return {
            "plan": plan,
            "current_stage": "planning_complete"
        }

    except Exception as e:
        logger.error(f"Planner failed: {e}")
        if client_id:
            from api.websocket import stream_agent_error
            asyncio.run(stream_agent_error(client_id, "planner", str(e)))
        return {"error": f"Planner failed: {str(e)}"}