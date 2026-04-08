import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from core.config import config
from core.prompts import REVIEW_SYSTEM
from core.utils import get_logger, parse_llm_json
from agents.state import AppState

logger = get_logger("review")

llm = ChatOpenAI(
    model=config.review_model,
    temperature=config.temperature,
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
        all_code = {
            "frontend": state.get("frontend_code", {}),
            "backend": state.get("backend_code", {}),
            "database": state.get("database_code", {}),
            "devops": state.get("devops_code", {})
        }

        messages = [
            SystemMessage(content=REVIEW_SYSTEM),
            HumanMessage(content=(
                f"Review this generated application for consistency issues:\n\n"
                f"Original plan:\n{state['plan']}\n\n"
                f"Generated code files:\n{all_code}"
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
            logger.info("Review passed — no issues found")
        else:
            logger.warning(
                f"Review found {len(review_result['issues'])} issues "
                f"({len(critical_issues)} critical)"
            )
            for issue in review_result["issues"]:
                logger.warning(
                    f"  [{issue['severity'].upper()}] "
                    f"{issue['file']}: {issue['issue']}"
                )

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