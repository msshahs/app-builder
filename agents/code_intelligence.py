import os
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from core.config import config
from core.utils import get_logger

logger = get_logger("code_intelligence")

llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    openai_api_key=config.openai_api_key,
    max_retries=3
)

CODE_INTELLIGENCE_SYSTEM = """You are a senior React/Node.js engineer doing a final code review and fix pass.

You will receive ALL generated frontend files at once. Your job is to:
1. Find ALL bugs that would prevent the app from working
2. Return ONLY the fixed versions of files that need changes

WHAT TO CHECK:
- App.jsx uses getToken() not isAuthenticated for route protection
- LoginPage and RegisterPage use useNavigate and redirect after success  
- RegisterPage has name, email, password fields and calls register(name, email, password)
- App-specific hooks (useTasks etc) export fetchX function wrapped in useCallback
- Dashboard passes onSubmit AND onClose to form modals
- Dashboard implements handleAdd/handleCreate that calls addItem then closes modal
- Form components call onSubmit(data) AND onClose() on submit
- Card components use item._id not item.id
- All API calls use /api/ prefix for non-auth routes
- All hooks use correct state setter variable name (setTasks not setItems)
- Navbar has working logout that calls logout() then navigate('/login')
- Empty states shown when list is empty
- Loading states shown when loading is true

RESPONSE FORMAT — return ONLY valid JSON:
{
  "issues_found": ["description of each issue found"],
  "fixed_files": {
    "frontend/src/App.jsx": "complete fixed file content",
    "frontend/src/pages/LoginPage.jsx": "complete fixed file content"
  }
}

Only include files in fixed_files if they actually need changes.
Return empty fixed_files if everything is correct.
Be thorough — find ALL issues in one pass."""


def read_all_frontend_files(project_dir: str) -> dict:
    """Read all generated frontend files."""
    files = {}
    src_dir = os.path.join(project_dir, "frontend/src")

    if not os.path.exists(src_dir):
        return files

    for root, dirs, filenames in os.walk(src_dir):
        # Skip node_modules
        dirs[:] = [d for d in dirs if d != "node_modules"]
        for fname in filenames:
            if fname.endswith((".jsx", ".js")):
                fpath = os.path.join(root, fname)
                rel_path = os.path.relpath(fpath, project_dir)
                try:
                    with open(fpath, "r") as f:
                        files[rel_path] = f.read()
                except:
                    pass

    return files


def apply_fixed_files(project_dir: str, fixed_files: dict) -> list:
    """Write fixed files back to disk."""
    applied = []
    for rel_path, content in fixed_files.items():
        full_path = os.path.join(project_dir, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)
        applied.append(rel_path)
        logger.info(f"Intelligence fix applied: {rel_path}")
    return applied


def run_code_intelligence(project_dir: str, spec: dict) -> dict:
    """
    Read all frontend files, send to LLM for review,
    apply fixes, return summary.
    """
    logger.info("Running code intelligence review...")

    # Read all frontend files
    all_files = read_all_frontend_files(project_dir)

    if not all_files:
        logger.warning("No frontend files found")
        return {"issues_found": [], "files_fixed": []}

    # Build the prompt with all file contents
    files_content = ""
    for path, content in all_files.items():
        files_content += f"\n\n=== {path} ===\n{content}"

    app_name = spec.get("app_name", "App")
    primary_color = spec.get("design", {}).get("primary_color", "violet")
    routes = spec.get("frontend_routes", [])
    api_contracts = spec.get("api_contracts", [])

    prompt = f"""Review and fix ALL issues in this generated React app.

App: {app_name}
Primary color: {primary_color}
Routes: {json.dumps(routes, indent=2)}
API contracts: {json.dumps(api_contracts, indent=2)}

ALL FRONTEND FILES:
{files_content}

Find every bug and return fixed versions of all files that need changes.
Be especially careful about:
1. App.jsx route protection using getToken() 
2. Auth pages redirecting after success
3. Hooks exporting all needed functions
4. Dashboard wiring form modals correctly
5. Form components calling both onSubmit and onClose"""

    try:
        response = llm.invoke([
            SystemMessage(content=CODE_INTELLIGENCE_SYSTEM),
            HumanMessage(content=prompt)
        ])

        # Parse response
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        result = json.loads(content)

        issues = result.get("issues_found", [])
        fixed_files = result.get("fixed_files", {})

        if issues:
            logger.info(f"Code intelligence found {len(issues)} issues:")
            for issue in issues:
                logger.info(f"  - {issue}")

        files_fixed = []
        if fixed_files:
            files_fixed = apply_fixed_files(project_dir, fixed_files)
            logger.info(f"Code intelligence fixed {len(files_fixed)} files")
        else:
            logger.info("Code intelligence: no fixes needed")

        return {
            "issues_found": issues,
            "files_fixed": files_fixed
        }

    except Exception as e:
        logger.error(f"Code intelligence failed: {e}")
        return {"issues_found": [], "files_fixed": [], "error": str(e)}