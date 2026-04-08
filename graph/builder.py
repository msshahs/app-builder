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


def should_continue_after_review(state: AppState) -> str:
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

    if critical_issues and attempts < 2:
        logger.info(f"Critical issues — retrying (attempt {attempts})")
        return "retry"

    return "end"


def build_graph() -> StateGraph:
    graph = StateGraph(AppState)

    graph.add_node("planner", planner_agent)
    graph.add_node("frontend", frontend_agent)
    graph.add_node("backend", backend_agent)
    graph.add_node("database", database_agent)
    graph.add_node("devops", devops_agent)
    graph.add_node("review", review_agent)

    graph.set_entry_point("planner")

    graph.add_edge("planner", "frontend")
    graph.add_edge("planner", "backend")
    graph.add_edge("planner", "database")
    graph.add_edge("planner", "devops")

    graph.add_edge("frontend", "review")
    graph.add_edge("backend", "review")
    graph.add_edge("database", "review")
    graph.add_edge("devops", "review")

    graph.add_conditional_edges(
        "review",
        should_continue_after_review,
        {
            "retry": "frontend",
            "end": END
        }
    )

    return graph.compile()