"""
Structural alignment fixes — safe post-generation corrections only.

These fixes handle cases where the LLM generates structurally correct code but
with minor omissions (missing routes in App.jsx, missing pages, wrong import style).

IMPORTANT: This module does NOT inject CRUD logic or rewrite business logic.
That would create new bugs. If the generated code is fundamentally wrong,
the review+fix_frontend loop handles it.
"""
import os
import re
from core.utils import get_logger

logger = get_logger("alignment")


def _read(path: str) -> str:
    try:
        with open(path) as f:
            return f.read()
    except Exception:
        return ""


def _write(path: str, content: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


def fix_named_imports(project_dir: str) -> list:
    """Fix default imports that must be named imports (e.g. getToken)."""
    issues = []
    src_dir = os.path.join(project_dir, "frontend/src")
    if not os.path.exists(src_dir):
        return issues

    for root, dirs, files in os.walk(src_dir):
        dirs[:] = [d for d in dirs if d != "node_modules"]
        for fname in files:
            if not fname.endswith((".jsx", ".js")):
                continue
            fpath = os.path.join(root, fname)
            content = _read(fpath)
            original = content

            # Fix: import getToken from '...' → import { getToken } from '...'
            content = re.sub(
                r"import getToken from '([^']*tokenStorage[^']*)'",
                r"import { getToken } from '\1'",
                content
            )
            content = re.sub(
                r'import getToken from "([^"]*tokenStorage[^"]*)"',
                r'import { getToken } from "\1"',
                content
            )

            if content != original:
                _write(fpath, content)
                issues.append(f"Fixed getToken named import in {fname}")

    return issues


def fix_missing_pages(project_dir: str, spec: dict) -> list:
    """Create stub pages for any routes defined in spec that are missing on disk."""
    issues = []
    routes = spec.get("frontend_routes", [])
    design = spec.get("design", {})
    primary = design.get("primary_color", "violet")

    for route in routes:
        if "component" not in route:
            continue
        component = route["component"]
        page_path = os.path.join(project_dir, f"frontend/src/pages/{component}.jsx")

        if not os.path.exists(page_path):
            issues.append(f"Missing page: {component} — creating stub")
            logger.info(f"Creating stub page: {component}")
            stub = f"""import React from 'react';

function {component}() {{
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-{primary}-600">{component}</h1>
      <p className="text-gray-500 mt-2">Page under construction.</p>
    </div>
  );
}}

export default {component};
"""
            _write(page_path, stub)

    return issues


def fix_app_jsx(project_dir: str, spec: dict) -> list:
    """Ensure App.jsx has routes for all pages defined in spec."""
    issues = []
    app_path = os.path.join(project_dir, "frontend/src/App.jsx")
    content = _read(app_path)

    if not content:
        logger.warning("App.jsx not found — skipping")
        return ["App.jsx missing"]

    routes = spec.get("frontend_routes", [])
    pages = [r for r in routes if "component" in r]

    # Check which routes are missing
    missing_routes = [
        r for r in pages
        if f'path="{r["path"]}"' not in content and f"path='{r['path']}'" not in content
    ]

    if not missing_routes:
        return issues

    # Only rebuild if routes are actually missing
    issues.append(f"App.jsx missing routes: {[r['path'] for r in missing_routes]}")
    logger.info(f"Rebuilding App.jsx — adding {len(missing_routes)} routes")
    _rebuild_app_jsx(project_dir, spec, content)

    return issues


def _rebuild_app_jsx(project_dir: str, spec: dict, current_content: str):
    """Rebuild App.jsx with all routes from spec."""
    design = spec.get("design", {})
    bg = design.get("background", "gray-50")
    routes = spec.get("frontend_routes", [])
    pages = [r for r in routes if "component" in r]

    imports = "import React from 'react';\n"
    imports += "import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';\n"
    imports += "import { getToken } from './utils/tokenStorage';\n"

    for route in pages:
        component = route["component"]
        imports += f"import {component} from './pages/{component}';\n"

    navbar_path = os.path.join(project_dir, "frontend/src/components/Navbar.jsx")
    if os.path.exists(navbar_path):
        imports += "import Navbar from './components/Navbar';\n"

    private_route = """
function PrivateRoute({ children }) {
  return getToken() ? children : <Navigate to="/login" replace />;
}
"""

    route_elements = []
    for route in routes:
        if "redirect" in route:
            route_elements.append(
                f'          <Route path="{route["path"]}" element={{<Navigate to="{route["redirect"]}" replace />}} />'
            )
        elif "component" in route:
            component = route["component"]
            if route.get("protected"):
                route_elements.append(
                    f'          <Route path="{route["path"]}" element={{<PrivateRoute><{component} /></PrivateRoute>}} />'
                )
            else:
                route_elements.append(
                    f'          <Route path="{route["path"]}" element={{<{component} />}} />'
                )

    has_navbar = os.path.exists(navbar_path)
    navbar_line = "        <Navbar />" if has_navbar else ""

    app_content = f"""{imports}
{private_route}
function App() {{
  return (
    <Router>
      <div className="min-h-screen bg-{bg}">
{navbar_line}
        <Routes>
{chr(10).join(route_elements)}
        </Routes>
      </div>
    </Router>
  );
}}

export default App;
"""
    _write(os.path.join(project_dir, "frontend/src/App.jsx"), app_content)
    logger.info("App.jsx rebuilt")


def run_alignment(project_dir: str, spec: dict) -> dict:
    """Run safe structural alignment checks. Returns summary."""
    logger.info(f"Running alignment for {project_dir}")
    all_issues = []

    all_issues.extend(fix_missing_pages(project_dir, spec))
    all_issues.extend(fix_app_jsx(project_dir, spec))
    all_issues.extend(fix_named_imports(project_dir))

    logger.info(f"Alignment complete — {len(all_issues)} issues fixed")
    return {
        "issues_fixed": len(all_issues),
        "details": all_issues
    }
