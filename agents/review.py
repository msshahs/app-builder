import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from core.config import config
from core.utils import get_logger, parse_llm_json
from agents.state import AppState

logger = get_logger("review")

llm = ChatOpenAI(
    model=config.review_model,
    temperature=0,
    openai_api_key=config.openai_api_key,
    max_retries=config.max_retries
)

REVIEW_SYSTEM = """You are a senior React/Node.js engineer doing a critical code review.

You review generated full-stack app code and find ONLY runtime-breaking issues.

CHECK THESE SPECIFIC THINGS:

1. App.jsx — uses getToken() from tokenStorage for route protection, NOT isAuthenticated
2. LoginPage — imports useNavigate, calls navigate('/dashboard') after successful login
3. RegisterPage — has name field, calls register(name, email, password), navigates after success
4. App-specific hooks (useTasks, useProducts etc):
   - wraps fetch function in useCallback
   - exports fetchX function in return statement
   - uses correct state setter (setTasks not setItems)
   - uses /api/ prefix for routes
5. Dashboard page:
   - passes BOTH onSubmit AND onClose to form modal
   - implements handleAdd/handleCreate function
   - uses item._id not item.id
6. Form components:
   - calls onSubmit(data) AND onClose() on submit
   - has Cancel button calling onClose()
7. Card components:
   - uses item._id for delete/update

DO NOT flag:
- Environment variables without hardcoded values (correct pattern)
- Template files (auth.js, server.js, User.js, useAuth.js) — these are correct
- Missing features or enhancements
- Style issues

Respond with ONLY valid JSON:
{
  "passed": true or false,
  "issues": [
    {
      "severity": "critical",
      "file": "frontend/src/pages/LoginPage.jsx",
      "issue": "LoginPage does not call navigate after login",
      "fix": "Add const navigate = useNavigate() and call navigate('/dashboard') after successful login"
    }
  ],
  "summary": "one paragraph summary"
}

Be strict about wiring issues. Be lenient about everything else.
If all wiring is correct, return passed: true with empty issues array."""


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
        # Build full code context for review
        frontend_code = state.get("frontend_code") or {}
        backend_code = state.get("backend_code") or {}

        if not frontend_code:
            logger.warning("No frontend code yet — skipping review")
            return {
                "review_result": {"passed": True, "issues": [], "summary": "No frontend code to review yet"},
                "review_attempts": attempts,
                "current_stage": "review_complete"
            }       

        # Only review frontend files — backend is handled by templates
        frontend_files = "\n\n".join([
            f"=== {path} ===\n{content}"
            for path, content in frontend_code.items()
        ])

        backend_routes = state.get("backend_routes", [])
        routes_context = "\n".join([
            f"  {r['method']} {r['path']}"
            for r in backend_routes
        ]) if backend_routes else "No routes extracted"

        messages = [
            SystemMessage(content=REVIEW_SYSTEM),
            HumanMessage(content=(
                f"Review this React frontend for wiring issues.\n\n"
                f"App: {state['plan'].get('app_name', 'App')}\n\n"
                f"Available backend routes:\n{routes_context}\n\n"
                f"Frontend files:\n{frontend_files}"
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
            logger.info("Review passed — no wiring issues found")
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