from typing import TypedDict, Optional, List, Callable, Any


class ReviewIssue(TypedDict):
    severity: str
    file: str
    issue: str
    fix: str


class ReviewResult(TypedDict):
    passed: bool
    issues: List[ReviewIssue]
    summary: str


class AppState(TypedDict):
    # Input
    user_prompt: str
    client_id: Optional[str]

    # Planner output
    plan: Optional[dict]

    # Parallel agent outputs
    frontend_code: Optional[dict]
    backend_code: Optional[dict]
    database_code: Optional[dict]
    devops_code: Optional[dict]

    # Review
    review_result: Optional[ReviewResult]
    review_attempts: int

    # Flow control
    approved: Optional[bool]
    error: Optional[str]
    current_stage: Optional[str]