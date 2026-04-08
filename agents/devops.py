import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from core.config import config
from core.prompts import DEVOPS_SYSTEM
from core.utils import get_logger, parse_llm_json, format_file_summary
from agents.state import AppState

logger = get_logger("devops")

llm = ChatOpenAI(
    model=config.planner_model,
    temperature=config.temperature,
    openai_api_key=config.openai_api_key,
    max_retries=config.max_retries
)


def devops_agent(state: AppState) -> AppState:
    logger.info("DevOps agent started")
    client_id = state.get("client_id")

    if state.get("error"):
        logger.warning("Skipping — previous agent failed")
        return {}

    if client_id:
        from api.websocket import stream_agent_start
        asyncio.run(stream_agent_start(client_id, "devops"))

    try:
        messages = [
            SystemMessage(content=DEVOPS_SYSTEM),
            HumanMessage(content=(
                f"Generate DevOps configuration for this app:\n\n"
                f"App name: {state['plan']['app_name']}\n"
                f"Tech stack: {state['plan']['tech_stack']}\n"
                f"Environment variables needed: {state['plan']['environment_variables']}"
            ))
        ]

        response = llm.invoke(messages)
        devops_code = parse_llm_json(response.content, "devops")

        if not devops_code:
            raise ValueError("DevOps agent returned invalid JSON")

        files = list(devops_code.keys())
        logger.info(f"DevOps complete:\n{format_file_summary(devops_code)}")

        if client_id:
            from api.websocket import stream_agent_complete
            asyncio.run(stream_agent_complete(client_id, "devops", files))

        return {"devops_code": devops_code}

    except Exception as e:
        logger.error(f"DevOps agent failed: {e}")
        if client_id:
            from api.websocket import stream_agent_error
            asyncio.run(stream_agent_error(client_id, "devops", str(e)))
        return {"error": f"DevOps failed: {str(e)}"}