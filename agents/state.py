from typing import TypedDict, Optional, List, Any


class ReviewIssue(TypedDict):
    severity: str
    file: str
    issue: str
    fix: str


class ReviewResult(TypedDict):
    passed: bool
    issues: List[ReviewIssue]
    summary: str


class APIContract(TypedDict):
    method: str
    path: str
    auth: bool
    request_body: Optional[dict]
    response_shape: str
    description: str


class ComponentSpec(TypedDict):
    name: str
    file: str
    description: str
    props: List[str]


class DesignSpec(TypedDict):
    style: str
    primary_color: str
    primary_shade: str
    background: str
    card_style: str
    font_style: str
    dark_mode: bool
    mood: str


class AppSpec(TypedDict):
    app_name: str
    description: str
    design: DesignSpec
    api_contracts: List[APIContract]
    frontend_routes: List[dict]
    component_specs: List[ComponentSpec]
    tech_stack: dict
    components: dict
    file_structure: List[str]
    environment_variables: List[str]


class BuildAttempt(TypedDict):
    attempt: int
    error: str
    fix_applied: str
    success: bool


class AppState(TypedDict):
    # Input
    user_prompt: str
    client_id: Optional[str]

    # Planner output
    plan: Optional[AppSpec]

    # Agent outputs
    frontend_code: Optional[dict]
    backend_code: Optional[dict]
    database_code: Optional[dict]
    devops_code: Optional[dict]

    # Derived from backend — what routes actually exist
    backend_routes: Optional[List[dict]]
    # Raw API contracts from plan (for frontend reference)
    api_contracts: Optional[List[APIContract]]
    # Resource naming info derived from api_contracts
    resource_info: Optional[dict]

    # Review
    review_result: Optional[ReviewResult]
    review_attempts: int

    # Build
    build_attempts: Optional[List[BuildAttempt]]
    build_success: Optional[bool]
    project_dir: Optional[str]
    project_id: Optional[str]

    # Deploy
    deploy_url: Optional[str]
    alb_dns: Optional[str]

    # Flow control
    approved: Optional[bool]
    error: Optional[str]
    current_stage: Optional[str]
