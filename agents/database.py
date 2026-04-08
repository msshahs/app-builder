import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from core.config import config
from core.prompts import DATABASE_SYSTEM
from core.utils import get_logger, parse_llm_json, format_file_summary
from agents.state import AppState

logger = get_logger("database")

llm = ChatOpenAI(
    model=config.codegen_model,
    temperature=config.temperature,
    openai_api_key=config.openai_api_key,
    max_retries=config.max_retries
)


def database_agent(state: AppState) -> AppState:
    logger.info("Database agent started")
    client_id = state.get("client_id")

    if state.get("error"):
        logger.warning("Skipping — previous agent failed")
        return {}

    if client_id:
        from api.websocket import stream_agent_start
        asyncio.run(stream_agent_start(client_id, "database"))

    try:
        messages = [
            SystemMessage(content=DATABASE_SYSTEM),
            HumanMessage(content=(
                f"Generate Mongoose models for this app:\n\n"
                f"Plan: {state['plan']}\n\n"
                f"Collections needed: {state['plan']['components']['database']['collections']}"
            ))
        ]

        response = llm.invoke(messages)
        database_code = parse_llm_json(response.content, "database")

        if not database_code:
            raise ValueError("Database agent returned invalid JSON")

        files = list(database_code.keys())
        logger.info(f"Database complete:\n{format_file_summary(database_code)}")

        if client_id:
            from api.websocket import stream_agent_complete
            asyncio.run(stream_agent_complete(client_id, "database", files))

        return {"database_code": database_code}

    except Exception as e:
        logger.error(f"Database agent failed: {e}")
        if client_id:
            from api.websocket import stream_agent_error
            asyncio.run(stream_agent_error(client_id, "database", str(e)))
        return {"error": f"Database failed: {str(e)}"}