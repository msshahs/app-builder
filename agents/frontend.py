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
        messages = [
            SystemMessage(content=FRONTEND_SYSTEM),
            HumanMessage(content=(
                f"Generate ALL frontend files for this app. Do not skip any file.\n\n"
                f"Plan: {state['plan']}\n\n"
                f"You MUST generate every frontend file listed here:\n"
                f"{chr(10).join([f for f in state['plan']['file_structure'] if f.startswith('frontend/')])}\n\n"
                f"Additionally always include:\n"
                f"- src/hooks/useAuth.js — JWT auth hook with login/logout/user state\n"
                f"- src/utils/api.js — Axios instance with REACT_APP_API_URL base URL and Authorization Bearer header interceptor\n"
                f"- src/utils/tokenStorage.js — localStorage utility for JWT get/set/remove\n"
                f"- src/pages/RegisterPage.jsx — registration form\n"
                f"- Every component and hook listed in the plan components section"
            ))
        ]

        response = llm.invoke(messages)
        frontend_code = parse_llm_json(response.content, "frontend")

        if not frontend_code:
            raise ValueError("Frontend agent returned invalid JSON")

        files = list(frontend_code.keys())
        logger.info(f"Frontend complete:\n{format_file_summary(frontend_code)}")

        if client_id:
            from api.websocket import stream_agent_complete
            asyncio.run(stream_agent_complete(client_id, "frontend", files))

        return {"frontend_code": frontend_code}

    except Exception as e:
        logger.error(f"Frontend agent failed: {e}")
        if client_id:
            from api.websocket import stream_agent_error
            asyncio.run(stream_agent_error(client_id, "frontend", str(e)))
        return {"error": f"Frontend failed: {str(e)}"}