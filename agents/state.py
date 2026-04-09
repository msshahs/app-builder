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


class RuntimeError(TypedDict):
    timestamp: str
    error: str
    fix_applied: str


class SmokeTestResult(TypedDict):
    endpoint: str
    passed: bool
    status_code: int
    error: Optional[str]


class AppState(TypedDict):
    # Input
    user_prompt: str
    client_id: Optional[str]

    # Planner output — full spec
    plan: Optional[AppSpec]

    # Parallel agent outputs
    frontend_code: Optional[dict]
    backend_code: Optional[dict]
    database_code: Optional[dict]
    devops_code: Optional[dict]

    # Review
    review_result: Optional[ReviewResult]
    review_attempts: int

    # Code alignment
    alignment_issues: Optional[List[str]]
    alignment_fixed: Optional[bool]

    # Build
    build_attempts: Optional[List[BuildAttempt]]
    build_success: Optional[bool]
    project_dir: Optional[str]
    project_id: Optional[str]

    # Deploy
    deploy_url: Optional[str]
    alb_dns: Optional[str]

    # Runtime monitoring
    runtime_errors: Optional[List[RuntimeError]]
    runtime_fix_attempts: int
    runtime_healthy: Optional[bool]

    # Smoke test
    smoke_test_results: Optional[List[SmokeTestResult]]
    smoke_test_passed: Optional[bool]

    # Flow control
    approved: Optional[bool]
    error: Optional[str]
    current_stage: Optional[str]