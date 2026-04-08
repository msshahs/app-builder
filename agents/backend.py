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
        messages = [
            SystemMessage(content=BACKEND_SYSTEM),
            HumanMessage(content=(
                f"Generate backend code for this app:\n\n"
                f"Plan: {state['plan']}\n\n"
                f"Generate these files: server.js, auth routes, "
                f"main feature routes, auth middleware, and error handler middleware"
            ))
        ]

        response = llm.invoke(messages)
        backend_code = parse_llm_json(response.content, "backend")

        if not backend_code:
            raise ValueError("Backend agent returned invalid JSON")

        files = list(backend_code.keys())
        logger.info(f"Backend complete:\n{format_file_summary(backend_code)}")

        if client_id:
            from api.websocket import stream_agent_complete
            asyncio.run(stream_agent_complete(client_id, "backend", files))

        return {"backend_code": backend_code}

    except Exception as e:
        logger.error(f"Backend agent failed: {e}")
        if client_id:
            from api.websocket import stream_agent_error
            asyncio.run(stream_agent_error(client_id, "backend", str(e)))
        return {"error": f"Backend failed: {str(e)}"}