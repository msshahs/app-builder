import os
import re
import json
from core.utils import get_logger

logger = get_logger("alignment")


def read_file(path: str) -> str:
    try:
        with open(path, "r") as f:
            return f.read()
    except:
        return ""


def write_file(path: str, content: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


def fix_app_jsx(project_dir: str, spec: dict) -> list:
    """Ensure App.jsx has all routes from spec."""
    issues = []
    app_path = os.path.join(project_dir, "frontend/src/App.jsx")
    content = read_file(app_path)

    if not content:
        logger.warning("App.jsx not found")
        return ["App.jsx missing"]

    routes = spec.get("frontend_routes", [])
    pages = [r for r in routes if "component" in r]

    missing_imports = []
    missing_routes = []

    for route in pages:
        component = route["component"]
        path = route["path"]

        if component not in content:
            missing_imports.append(component)
        if f'path="{path}"' not in content and f"path='{path}'" not in content:
            missing_routes.append(route)

    if missing_imports or missing_routes:
        issues.append(f"App.jsx missing routes: {[r['path'] for r in missing_routes]}")
        logger.info(f"Fixing App.jsx — adding {len(missing_routes)} missing routes")
        _rebuild_app_jsx(project_dir, spec, content)

    return issues


def fix_named_imports(project_dir: str) -> list:
    """Fix default imports that should be named imports."""
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
            content = read_file(fpath)
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
                write_file(fpath, content)
                issues.append(f"Fixed getToken import in {fname}")

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
        page_dir = "pages"
        imports += f"import {component} from './{page_dir}/{component}';\n"

    # Add Navbar if it exists
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

    has_navbar = os.path.exists(os.path.join(project_dir, "frontend/src/components/Navbar.jsx"))
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

    write_file(os.path.join(project_dir, "frontend/src/App.jsx"), app_content)
    logger.info("App.jsx rebuilt with all routes")


def fix_register_page(project_dir: str, spec: dict) -> list:
    """Ensure RegisterPage has name field and correct styling."""
    issues = []
    register_path = os.path.join(project_dir, "frontend/src/pages/RegisterPage.jsx")
    content = read_file(register_path)

    if not content:
        issues.append("RegisterPage.jsx missing — creating")
        _create_register_page(project_dir, spec)
        return issues

    needs_fix = False
    if "name" not in content or "setName" not in content:
        issues.append("RegisterPage missing name field")
        needs_fix = True

    if 'register(email' in content and 'register(name' not in content:
        issues.append("RegisterPage calling register without name argument")
        needs_fix = True

    if needs_fix:
        logger.info("Fixing RegisterPage — adding name field")
        _create_register_page(project_dir, spec)

    return issues


def _create_register_page(project_dir: str, spec: dict):
    design = spec.get("design", {})
    primary = design.get("primary_color", "violet")
    bg = design.get("background", "gray-50")
    app_name = spec.get("app_name", "App")

    content = f"""import React, {{ useState }} from 'react';
import {{ useAuth }} from '../hooks/useAuth';
import {{ useNavigate, Link }} from 'react-router-dom';

function RegisterPage() {{
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const {{ register, error, loading }} = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {{
    e.preventDefault();
    const success = await register(name, email, password);
    if (success) navigate('/dashboard');
  }};

  return (
    <div className="min-h-screen bg-{bg} flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md">
        <h1 className="text-2xl font-bold text-{primary}-600 text-center mb-6">{app_name}</h1>
        <p className="text-gray-500 text-center text-sm mb-6">Create your account</p>
        {{error && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-xl mb-4">
            {{error}}
          </div>
        )}}
        <form onSubmit={{handleSubmit}} className="space-y-4">
          <input
            type="text"
            placeholder="Full Name"
            value={{name}}
            onChange={{(e) => setName(e.target.value)}}
            className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-{primary}-500 focus:border-transparent outline-none"
            required
          />
          <input
            type="email"
            placeholder="Email address"
            value={{email}}
            onChange={{(e) => setEmail(e.target.value)}}
            className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-{primary}-500 focus:border-transparent outline-none"
            required
          />
          <input
            type="password"
            placeholder="Password (min 6 characters)"
            value={{password}}
            onChange={{(e) => setPassword(e.target.value)}}
            className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-{primary}-500 focus:border-transparent outline-none"
            required
            minLength={{6}}
          />
          <button
            type="submit"
            disabled={{loading}}
            className="w-full py-3 rounded-xl font-semibold text-white bg-{primary}-600 hover:bg-{primary}-700 transition-colors disabled:opacity-70 disabled:cursor-not-allowed"
          >
            {{loading ? 'Creating account...' : 'Create Account'}}
          </button>
        </form>
        <p className="text-center text-sm text-gray-500 mt-6">
          Already have an account? {{' '}}
          <Link to="/login" className="text-{primary}-600 font-medium hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  );
}}

export default RegisterPage;
"""
    write_file(os.path.join(project_dir, "frontend/src/pages/RegisterPage.jsx"), content)
    logger.info("RegisterPage created with name field")


def fix_login_page(project_dir: str, spec: dict) -> list:
    """Ensure LoginPage has correct styling and fields."""
    issues = []
    login_path = os.path.join(project_dir, "frontend/src/pages/LoginPage.jsx")
    content = read_file(login_path)

    if not content:
        issues.append("LoginPage.jsx missing — creating")
        _create_login_page(project_dir, spec)

    return issues


def _create_login_page(project_dir: str, spec: dict):
    design = spec.get("design", {})
    primary = design.get("primary_color", "violet")
    bg = design.get("background", "gray-50")
    app_name = spec.get("app_name", "App")

    content = f"""import React, {{ useState }} from 'react';
import {{ useAuth }} from '../hooks/useAuth';
import {{ useNavigate, Link }} from 'react-router-dom';

function LoginPage() {{
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const {{ login, error, loading }} = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {{
    e.preventDefault();
    const success = await login(email, password);
    if (success) navigate('/dashboard');
  }};

  return (
    <div className="min-h-screen bg-{bg} flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md">
        <h1 className="text-2xl font-bold text-{primary}-600 text-center mb-6">{app_name}</h1>
        <p className="text-gray-500 text-center text-sm mb-6">Sign in to your account</p>
        {{error && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-xl mb-4">
            {{error}}
          </div>
        )}}
        <form onSubmit={{handleSubmit}} className="space-y-4">
          <input
            type="email"
            placeholder="Email address"
            value={{email}}
            onChange={{(e) => setEmail(e.target.value)}}
            className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-{primary}-500 focus:border-transparent outline-none"
            required
          />
          <input
            type="password"
            placeholder="Password"
            value={{password}}
            onChange={{(e) => setPassword(e.target.value)}}
            className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-{primary}-500 focus:border-transparent outline-none"
            required
          />
          <button
            type="submit"
            disabled={{loading}}
            className="w-full py-3 rounded-xl font-semibold text-white bg-{primary}-600 hover:bg-{primary}-700 transition-colors disabled:opacity-70 disabled:cursor-not-allowed"
          >
            {{loading ? 'Signing in...' : 'Sign In'}}
          </button>
        </form>
        <p className="text-center text-sm text-gray-500 mt-6">
          Don't have an account? {{' '}}
          <Link to="/register" className="text-{primary}-600 font-medium hover:underline">Create one</Link>
        </p>
      </div>
    </div>
  );
}}

export default LoginPage;
"""
    write_file(os.path.join(project_dir, "frontend/src/pages/LoginPage.jsx"), content)
    logger.info("LoginPage created")


def fix_api_calls(project_dir: str, spec: dict) -> list:
    """Fix all API calls to use correct paths from spec."""
    issues = []
    contracts = spec.get("api_contracts", [])
    valid_paths = [c["path"] for c in contracts]

    src_dir = os.path.join(project_dir, "frontend/src")
    if not os.path.exists(src_dir):
        return issues

    for root, dirs, files in os.walk(src_dir):
        for fname in files:
            if not fname.endswith((".jsx", ".js")):
                continue
            fpath = os.path.join(root, fname)
            content = read_file(fpath)
            original = content

            # Fix: api.get('/tasks') → api.get('/api/tasks')
            for path in valid_paths:
                if path.startswith("/api/"):
                    resource = path.replace("/api/", "/")
                    # Replace bare resource paths with /api/ prefix
                    patterns = [
                        (f"api.get('{resource}'", f"api.get('{path}'"),
                        (f'api.get("{resource}"', f'api.get("{path}"'),
                        (f"api.post('{resource}'", f"api.post('{path}'"),
                        (f'api.post("{resource}"', f'api.post("{path}"'),
                        (f"api.put('{resource}", f"api.put('{path}"),
                        (f'api.put("{resource}', f'api.put("{path}'),
                        (f"api.delete('{resource}", f"api.delete('{path}"),
                        (f'api.delete("{resource}', f'api.delete("{path}'),
                    ]
                    for old, new in patterns:
                        content = content.replace(old, new)

            if content != original:
                write_file(fpath, content)
                issues.append(f"Fixed API paths in {fname}")
                logger.info(f"Fixed API paths in {fname}")

    return issues


def _get_state_setter_name(content: str, resource: str) -> str:
    """Find the actual state setter name used in the hook."""
    # Look for useState patterns like: const [tasks, setTasks] = useState
    pattern = r'const \[(\w+),\s*(\w+)\]\s*=\s*useState\(\[\]'
    match = re.search(pattern, content)
    if match:
        return match.group(2)  # returns setTasks, setProducts, etc.
    # Fallback — derive from resource name
    resource_singular = resource.rstrip("s")
    return f"set{resource_singular.capitalize()}s"


def _inject_crud_methods(content: str, resource: str, spec: dict) -> str:
    """Add CRUD methods to a hook if missing."""
    resource_singular = resource.rstrip("s")
    Resource = resource_singular.capitalize()
    setter = _get_state_setter_name(content, resource)

    crud = f"""
  const add{Resource} = async (data) => {{
    try {{
      const response = await api.post('/api/{resource}', data);
      {setter}(prev => [...prev, response.data]);
      return response.data;
    }} catch (err) {{
      setError(err.response?.data?.message || 'Failed to create');
      return null;
    }}
  }};

  const update{Resource} = async (id, data) => {{
    try {{
      const response = await api.put(`/api/{resource}/${{id}}`, data);
      {setter}(prev => prev.map(item => item._id === id ? response.data : item));
      return response.data;
    }} catch (err) {{
      setError(err.response?.data?.message || 'Failed to update');
      return null;
    }}
  }};

  const delete{Resource} = async (id) => {{
    try {{
      await api.delete(`/api/{resource}/${{id}}`);
      {setter}(prev => prev.filter(item => item._id !== id));
      return true;
    }} catch (err) {{
      setError(err.response?.data?.message || 'Failed to delete');
      return false;
    }}
  }};
"""
    content = content.replace("\n  return {", crud + "\n  return {")
    return content


def fix_response_data(project_dir: str, spec: dict) -> list:
    """Fix response.data handling and ensure fetchResource + CRUD exported."""
    issues = []
    hooks_dir = os.path.join(project_dir, "frontend/src/hooks")
    if not os.path.exists(hooks_dir):
        return issues

    for fname in os.listdir(hooks_dir):
        if fname == "useAuth.js" or not fname.endswith(".js"):
            continue

        fpath = os.path.join(hooks_dir, fname)
        content = read_file(fpath)
        original = content

        # Find state variable name dynamically
        state_match = re.search(r'const \[(\w+),\s*(\w+)\]\s*=\s*useState\(\[\]', content)
        if not state_match:
            continue

        state_var = state_match.group(1)   # e.g. tasks
        setter_var = state_match.group(2)  # e.g. setTasks

        # Fix setX(response.data) → safe array handling
        bad_pattern = f"{setter_var}(response.data)"
        if bad_pattern in content:
            content = content.replace(
                bad_pattern,
                f"{setter_var}(Array.isArray(response.data) ? response.data : response.data.{state_var} || response.data.items || response.data.data || [])"
            )
            issues.append(f"Fixed response.data in {fname}")

        # Find resource name from API call
        resource_match = re.search(r'api\.(get|post)\([\'\"]/api/(\w+)', content)
        if resource_match:
            resource = resource_match.group(2)
            resource_singular = resource.rstrip("s")
            Resource = resource_singular.capitalize()

            # Add CRUD methods if missing
            if f"add{Resource}" not in content:
                content = _inject_crud_methods(content, resource, spec)
                issues.append(f"Injected CRUD methods in {fname}")

            # Ensure fetchResource function exists and is exported
            fetch_fn_name = f"fetch{Resource.capitalize()}s" if not resource.endswith("s") else f"fetch{Resource.capitalize()}"
            # Simplify — just ensure a fetchX function exists
            if "const fetch" not in content:
                # Extract the useEffect fetch logic into a named function
                content = _extract_fetch_function(content, resource, state_var, setter_var)
                issues.append(f"Extracted fetch function in {fname}")

            # Ensure return exports all methods
            content = _ensure_return_exports(content, state_var, resource_singular)

        if content != original:
            write_file(fpath, content)
            logger.info(f"Fixed {fname}")

    return issues


def _extract_fetch_function(content: str, resource: str, state_var: str, setter_var: str) -> str:
    """Extract inline useEffect fetch into a named fetchX function."""
    fetch_fn = f"""
  const fetch{resource.capitalize()} = async () => {{
    try {{
      setLoading(true);
      const response = await api.get('/api/{resource}');
      {setter_var}(Array.isArray(response.data) ? response.data : response.data.{state_var} || response.data.items || []);
    }} catch (err) {{
      setError(err.response?.data?.message || 'Failed to load');
      {setter_var}([]);
    }} finally {{
      setLoading(false);
    }}
  }};

  useEffect(() => {{
    fetch{resource.capitalize()}();
  }}, []);
"""
    # Replace the old useEffect with the new named function
    content = re.sub(
        r'useEffect\(\(\) => \{.*?fetchTasks\(\);.*?\}, \[\]\);',
        fetch_fn,
        content,
        flags=re.DOTALL
    )
    # Also replace inline useEffect fetch patterns
    content = re.sub(
        r'useEffect\(\(\) => \{[\s\S]*?const fetch\w+ = async.*?\}\);',
        fetch_fn,
        content,
        flags=re.DOTALL
    )
    return content


def _ensure_return_exports(content: str, state_var: str, resource_singular: str) -> str:
    """Ensure the hook's return statement exports all necessary methods."""
    Resource = resource_singular.capitalize()

    # Find existing return statement
    return_match = re.search(r'return \{([^}]+)\}', content)
    if not return_match:
        return content

    existing_exports = return_match.group(1)
    new_exports = existing_exports

    # Add missing exports
    needed = [
        state_var,
        f"fetch{Resource}s" if not state_var.endswith("s") else f"fetch{state_var[0].upper() + state_var[1:]}",
        f"add{Resource}",
        f"update{Resource}",
        f"delete{Resource}",
        "loading",
        "error"
    ]

    for export in needed:
        if export not in existing_exports:
            # Also check if function exists in content
            if export in content or export == state_var:
                new_exports = new_exports.rstrip() + f", {export}"

    if new_exports != existing_exports:
        content = content.replace(
            f"return {{{existing_exports}}}",
            f"return {{{new_exports}}}"
        )

    return content

def fix_missing_pages(project_dir: str, spec: dict) -> list:
    """Create any missing pages defined in spec."""
    issues = []
    routes = spec.get("frontend_routes", [])

    for route in routes:
        if "component" not in route:
            continue
        component = route["component"]
        page_path = os.path.join(project_dir, f"frontend/src/pages/{component}.jsx")

        if not os.path.exists(page_path):
            issues.append(f"Missing page: {component}")
            logger.info(f"Creating missing page: {component}")
            _create_generic_page(project_dir, component, spec)

    return issues

def fix_hooks_exports(project_dir: str) -> list:
    """Ensure all hooks export fetchX function so components can call it."""
    issues = []
    hooks_dir = os.path.join(project_dir, "frontend/src/hooks")
    if not os.path.exists(hooks_dir):
        return issues

    for fname in os.listdir(hooks_dir):
        if fname == "useAuth.js" or not fname.endswith(".js"):
            continue

        fpath = os.path.join(hooks_dir, fname)
        content = read_file(fpath)
        original = content

        # Find all const fetch functions
        fetch_fns = re.findall(r'const (fetch\w+)\s*=\s*async', content)

        if not fetch_fns:
            continue

        # Check if they're in the return statement
        return_match = re.search(r'return \{([^}]+)\}', content)
        if not return_match:
            continue

        existing_exports = return_match.group(1)
        missing = [fn for fn in fetch_fns if fn not in existing_exports]

        if missing:
            new_exports = existing_exports.rstrip() + ", " + ", ".join(missing)
            content = content.replace(
                f"return {{{existing_exports}}}",
                f"return {{{new_exports}}}"
            )
            issues.append(f"Added missing exports to {fname}: {missing}")
            write_file(fpath, content)
            logger.info(f"Fixed exports in {fname}: added {missing}")

    return issues

def _create_generic_page(project_dir: str, component: str, spec: dict):
    design = spec.get("design", {})
    primary = design.get("primary_color", "violet")

    content = f"""import React from 'react';

function {component}() {{
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-{primary}-600">{component}</h1>
      <p className="text-gray-500 mt-2">Content coming soon...</p>
    </div>
  );
}}

export default {component};
"""
    write_file(os.path.join(project_dir, f"frontend/src/pages/{component}.jsx"), content)

def fix_navigation(project_dir: str, spec: dict) -> list:
    """Ensure all auth pages use useNavigate and redirect after success."""
    issues = []
    pages_dir = os.path.join(project_dir, "frontend/src/pages")
    
    if not os.path.exists(pages_dir):
        return issues

    for fname in ["LoginPage.jsx", "RegisterPage.jsx"]:
        fpath = os.path.join(pages_dir, fname)
        content = read_file(fpath)
        if not content:
            continue

        original = content
        needs_fix = False

        # Add useNavigate import if missing
        if "useNavigate" not in content:
            content = content.replace(
                "import { Link }",
                "import { Link, useNavigate }"
            ).replace(
                "from 'react-router-dom';",
                "from 'react-router-dom';"
            )
            if "useNavigate" not in content:
                content = content.replace(
                    "from 'react-router-dom';",
                    "from 'react-router-dom';\n"
                )
            needs_fix = True

        # Add navigate hook if missing
        if "useNavigate" in content and "const navigate = useNavigate()" not in content:
            content = content.replace(
                "const { login }",
                "const navigate = useNavigate();\n  const { login }"
            ).replace(
                "const { register }",
                "const navigate = useNavigate();\n  const { register }"
            )
            needs_fix = True

        # Add redirect after login
        if "await login(" in content and "navigate(" not in content:
            content = content.replace(
                "await login(email, password);",
                "const result = await login(email, password);\n      if (result) navigate('/dashboard');"
            )
            needs_fix = True

        # Add redirect after register
        if "await register(" in content and "navigate(" not in content:
            content = content.replace(
                "await register(name, email, password);",
                "const result = await register(name, email, password);\n      if (result) navigate('/dashboard');"
            )
            needs_fix = True

        if content != original or needs_fix:
            write_file(fpath, content)
            issues.append(f"Fixed navigation in {fname}")
            logger.info(f"Fixed navigation in {fname}")

    return issues

def run_alignment(project_dir: str, spec: dict) -> dict:
    """Run all alignment checks and fixes. Returns summary."""
    logger.info(f"Running code alignment for {project_dir}")
    all_issues = []

    all_issues.extend(fix_missing_pages(project_dir, spec))
    all_issues.extend(fix_app_jsx(project_dir, spec))
    all_issues.extend(fix_register_page(project_dir, spec))
    all_issues.extend(fix_login_page(project_dir, spec))
    all_issues.extend(fix_navigation(project_dir, spec)) 
    all_issues.extend(fix_api_calls(project_dir, spec))
    all_issues.extend(fix_response_data(project_dir, spec))
    all_issues.extend(fix_hooks_exports(project_dir))  
    all_issues.extend(fix_named_imports(project_dir))

    logger.info(f"Alignment complete — {len(all_issues)} issues fixed")
    return {
        "issues_fixed": len(all_issues),
        "details": all_issues
    }