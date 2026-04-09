from langgraph.graph import StateGraph, END
from agents.state import AppState
from agents.planner import planner_agent
from agents.frontend import frontend_agent
from agents.backend import backend_agent
from agents.database import database_agent
from agents.devops import devops_agent
from agents.review import review_agent
from core.utils import get_logger

logger = get_logger("graph")

MAX_FIX_ATTEMPTS = 3


def should_retry_after_review(state: AppState) -> str:
    """Decide whether to fix frontend or proceed."""
    if state.get("error"):
        return "end"

    review = state.get("review_result")
    attempts = state.get("review_attempts", 0)

    if not review:
        return "end"

    critical_issues = [
        i for i in review.get("issues", [])
        if i.get("severity") == "critical"
    ]

    if critical_issues and attempts < MAX_FIX_ATTEMPTS:
        logger.info(f"Critical issues found — retrying frontend (attempt {attempts + 1}/{MAX_FIX_ATTEMPTS})")
        return "fix_frontend"

    return "end"


def fix_frontend_agent(state: AppState) -> AppState:
    """Fix frontend based on review issues — reads backend + review context."""
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage
    from core.config import config
    from core.prompts import FRONTEND_SYSTEM
    from core.utils import parse_llm_json, format_file_summary

    logger.info("Fix frontend agent started")
    client_id = state.get("client_id")

    review = state.get("review_result", {})
    issues = review.get("issues", [])
    critical = [i for i in issues if i.get("severity") == "critical"]

    if not critical:
        return {}

    llm = ChatOpenAI(
        model=config.codegen_model,
        temperature=0,
        openai_api_key=config.openai_api_key,
        max_retries=config.max_retries
    )

    # Build context with all current frontend files
    existing_frontend = state.get("frontend_code", {})
    files_context = "\n\n".join([
        f"=== {path} ===\n{content}"
        for path, content in existing_frontend.items()
    ])

    issues_context = "\n".join([
        f"- [{i['severity'].upper()}] {i['file']}: {i['issue']} → Fix: {i['fix']}"
        for i in critical
    ])

    try:
        messages = [
            SystemMessage(content=FRONTEND_SYSTEM),
            HumanMessage(content=(
                f"Fix these CRITICAL issues in the frontend code.\n\n"
                f"ISSUES TO FIX:\n{issues_context}\n\n"
                f"CURRENT FRONTEND FILES:\n{files_context}\n\n"
                f"Backend routes available:\n"
                "\n".join([r['method'] + ' ' + r['path'] for r in state.get('backend_routes', [])]) + "\n\n",
                f"Return ONLY the fixed files in JSON format.\n"
                f"Include ONLY files that need changes.\n"
                f"Keep all other files exactly as they are."
            ))
        ]

        response = llm.invoke(messages)
        fixed_code = parse_llm_json(response.content, "fix_frontend")

        if fixed_code:
            # Merge fixed files into existing frontend code
            updated_frontend = {**existing_frontend, **fixed_code}
            logger.info(f"Fixed {len(fixed_code)} files:\n{format_file_summary(fixed_code)}")

            return {
                "frontend_code": updated_frontend,
                "review_attempts": state.get("review_attempts", 0) + 1
            }

    except Exception as e:
        logger.error(f"Fix frontend agent failed: {e}")

    return {"review_attempts": state.get("review_attempts", 0) + 1}


def build_graph() -> StateGraph:
    graph = StateGraph(AppState)

    graph.add_node("planner", planner_agent)
    graph.add_node("backend", backend_agent)
    graph.add_node("database", database_agent)
    graph.add_node("devops", devops_agent)
    graph.add_node("frontend", frontend_agent)
    graph.add_node("review", review_agent)
    graph.add_node("fix_frontend", fix_frontend_agent)

    graph.set_entry_point("planner")

    # Backend, database, devops run after planner
    graph.add_edge("planner", "backend")
    graph.add_edge("planner", "database")
    graph.add_edge("planner", "devops")

    # Frontend runs after backend (reads backend routes)
    graph.add_edge("backend", "frontend")

    # Only frontend triggers review
    graph.add_edge("frontend", "review")

    graph.add_conditional_edges(
        "review",
        should_retry_after_review,
        {
            "fix_frontend": "fix_frontend",
            "end": END
        }
    )

    graph.add_edge("fix_frontend", "review")

    return graph.compile()