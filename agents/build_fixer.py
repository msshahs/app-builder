import os
import re
import json
from deploy.docker_builder import run_command
from core.utils import get_logger

logger = get_logger("build_fixer")

# Known build error patterns and their fixes
BUILD_ERROR_PATTERNS = [
    {
        "pattern": r"Rollup failed to resolve import ['\"]([^'\"]+)['\"]",
        "description": "Missing npm package",
        "fix": "add_npm_package"
    },
    {
        "pattern": r"Cannot find module '([^']+)'",
        "description": "Missing node module",
        "fix": "add_npm_package"
    },
    {
        "pattern": r"Cannot find module '/app/server\.js'",
        "description": "Wrong CMD path in Dockerfile",
        "fix": "fix_dockerfile_cmd"
    },
    {
        "pattern": r'"/app/build".*not found',
        "description": "Dockerfile copies from /app/build but Vite outputs to /app/dist",
        "fix": "fix_dockerfile_dist"
    },
    {
        "pattern": r"No matching version found for ([^\s]+)",
        "description": "Invalid package version",
        "fix": "fix_package_version"
    },
    {
        "pattern": r'"(\w+)" is not exported by "([^"]+)", imported by "src/pages/([^"]+)"',
        "description": "Wrong import — function not exported by that file",
        "fix": "fix_wrong_import"
    },
    {
        "pattern": r'"(\w+)" is not exported by "([^"]+)", imported by "src/([^"]+)"',
        "description": "Wrong import — function not exported by that file",
        "fix": "fix_wrong_import"
    },
    {
        "pattern": r"SyntaxError.*in (.*\.jsx?)",
        "description": "Syntax error in file",
        "fix": "report_syntax_error"
    },
    {
        "pattern": r'"default" is not exported by "([^"]+)", imported by "src/([^"]+)"',
        "description": "Default import but file uses named exports",
        "fix": "fix_default_import"
    },
]


def add_npm_package(package_name: str, frontend_dir: str):
    """Add a missing package to package.json."""
    # Skip relative imports and node built-ins
    if package_name.startswith(".") or package_name.startswith("/"):
        return False
    if package_name in ["path", "fs", "os", "http", "https", "crypto"]:
        return False

    # Known package versions
    KNOWN_VERSIONS = {
        "lucide-react": "^0.363.0",
        "prop-types": "^15.8.1",
        "react-router-dom": "^6.20.0",
        "axios": "^1.6.2",
        "date-fns": "^3.0.0",
        "clsx": "^2.0.0",
        "framer-motion": "^11.0.0",
        "recharts": "^2.10.0",
        "react-hook-form": "^7.49.0",
        "zod": "^3.22.0",
        "@headlessui/react": "^1.7.17",
        "uuid": "^9.0.0",
    }

    package_path = os.path.join(frontend_dir, "package.json")
    try:
        with open(package_path, "r") as f:
            pkg = json.load(f)

        # Get base package name (handle scoped packages)
        base_name = package_name.split("/")[0]
        if package_name.startswith("@"):
            base_name = "/".join(package_name.split("/")[:2])

        if base_name not in pkg.get("dependencies", {}):
            version = KNOWN_VERSIONS.get(base_name, "latest")
            pkg["dependencies"][base_name] = version

            with open(package_path, "w") as f:
                json.dump(pkg, f, indent=2)

            logger.info(f"Added {base_name}@{version} to package.json")
            return True
    except Exception as e:
        logger.error(f"Failed to add package {package_name}: {e}")
    return False


def fix_dockerfile_cmd(frontend_dir: str):
    """Fix CMD in backend Dockerfile."""
    dockerfile_path = os.path.join(frontend_dir, "Dockerfile")
    if not os.path.exists(dockerfile_path):
        return

    with open(dockerfile_path, "r") as f:
        content = f.read()

    content = content.replace(
        'CMD ["node", "server.js"]',
        'CMD ["node", "src/server.js"]'
    )

    with open(dockerfile_path, "w") as f:
        f.write(content)

    logger.info("Fixed Dockerfile CMD to use src/server.js")


def fix_dockerfile_dist(frontend_dir: str):
    """Fix Dockerfile to copy from /app/dist instead of /app/build."""
    dockerfile_path = os.path.join(frontend_dir, "Dockerfile")
    if not os.path.exists(dockerfile_path):
        return

    with open(dockerfile_path, "r") as f:
        content = f.read()

    content = content.replace(
        "COPY --from=build /app/build",
        "COPY --from=build /app/dist"
    ).replace(
        "COPY --from=0 /app/build",
        "COPY --from=0 /app/dist"
    )

    with open(dockerfile_path, "w") as f:
        f.write(content)

    logger.info("Fixed Dockerfile to copy from /app/dist")


def fix_wrong_import(exported_name: str, source_file: str, importing_file: str, project_dir: str) -> bool:
    """Fix wrong imports — e.g. importing login from api.js instead of useAuth."""
    # Auth functions must come from useAuth, never from api.js
    AUTH_FUNCTIONS = {"login", "register", "logout", "getToken", "setToken"}

    if exported_name not in AUTH_FUNCTIONS:
        return False

    # Find the actual file
    frontend_dir = os.path.join(project_dir, "frontend", "src")
    possible_paths = [
        os.path.join(project_dir, "frontend", "src", importing_file),
        os.path.join(project_dir, "frontend", importing_file),
    ]

    full_path = None
    for p in possible_paths:
        if os.path.exists(p):
            full_path = p
            break

    if not full_path:
        return False

    with open(full_path, "r") as f:
        content = f.read()

    original = content

    # Remove wrong import line
    content = re.sub(
        rf"import \{{ {exported_name}[^}}]*\}} from '[^']*api[^']*';\n?",
        "",
        content
    )

    # If useAuth not already imported, add it
    if "useAuth" not in content and exported_name in {"login", "register", "logout"}:
        content = content.replace(
            "import React",
            "import { useAuth } from '../hooks/useAuth';\nimport React"
        )

    if content != original:
        with open(full_path, "w") as f:
            f.write(content)
        logger.info(f"Fixed wrong import of '{exported_name}' in {importing_file}")
        return True

    return False


def fix_default_import(source_file: str, importing_file: str, project_dir: str) -> bool:
    """Fix default import to named import."""
    NAMED_EXPORT_FILES = {
        "src/utils/tokenStorage.js": "getToken",
        "src/utils/api.js": "api",
    }

    fix_name = NAMED_EXPORT_FILES.get(source_file)
    if not fix_name:
        return False

    full_path = os.path.join(project_dir, "frontend", "src", importing_file)
    if not os.path.exists(full_path):
        return False

    with open(full_path, "r") as f:
        content = f.read()

    original = content
    # Fix: import getToken from '...' → import { getToken } from '...'
    content = re.sub(
        rf"import {fix_name} from '([^']*tokenStorage[^']*)'",
        f"import {{ {fix_name} }} from '\\1'",
        content
    )
    content = re.sub(
        rf'import {fix_name} from "([^"]*tokenStorage[^"]*)"',
        f'import {{ {fix_name} }} from "\\1"',
        content
    )

    if content != original:
        with open(full_path, "w") as f:
            f.write(content)
        logger.info(f"Fixed default import of '{fix_name}' in {importing_file}")
        return True

    return False

def attempt_fix(error_output: str, project_dir: str) -> tuple[bool, str]:
    """Try to fix a build error. Returns (fixed, description)."""
    frontend_dir = os.path.join(project_dir, "frontend")
    backend_dir = os.path.join(project_dir, "backend")

    for pattern_info in BUILD_ERROR_PATTERNS:
        match = re.search(pattern_info["pattern"], error_output, re.IGNORECASE)
        if not match:
            continue

        fix_type = pattern_info["fix"]
        description = pattern_info["description"]

        logger.info(f"Build error detected: {description}")

        if fix_type == "add_npm_package":
            package = match.group(1)
            if "frontend" in error_output.lower() or "vite" in error_output.lower():
                fixed = add_npm_package(package, frontend_dir)
            else:
                fixed = add_npm_package(package, backend_dir)
            if fixed:
                return True, f"Added missing package: {package}"

        elif fix_type == "fix_wrong_import":
            exported_name = match.group(1)
            source_file = match.group(2)
            importing_file = match.group(3)
            fixed = fix_wrong_import(exported_name, source_file, importing_file, project_dir)
            if fixed:
                return True, f"Fixed wrong import of '{exported_name}' from '{source_file}'"

        elif fix_type == "fix_dockerfile_cmd":
            fix_dockerfile_cmd(backend_dir)
            return True, "Fixed Dockerfile CMD path"

        elif fix_type == "fix_dockerfile_dist":
            fix_dockerfile_dist(frontend_dir)
            return True, "Fixed Dockerfile dist path"
        
        elif fix_type == "fix_default_import":
            source_file = match.group(1)
            importing_file = match.group(2)
            fixed = fix_default_import(source_file, importing_file, project_dir)
            if fixed:
                return True, f"Fixed default import in {importing_file}"

        elif fix_type == "report_syntax_error":
            file_path = match.group(1)
            return False, f"Syntax error in {file_path} — needs manual fix"

    return False, "Unknown build error — no fix available"


async def build_with_healing(
    project_id: str,
    project_dir: str,
    build_fn,
    max_attempts: int = 3
) -> dict:
    """Attempt build with automatic error fixing."""
    attempts = []

    for attempt in range(1, max_attempts + 1):
        logger.info(f"Build attempt {attempt}/{max_attempts}")

        try:
            result = await build_fn()
            logger.info(f"Build succeeded on attempt {attempt}")
            return {
                "success": True,
                "attempts": attempts,
                "final_attempt": attempt
            }
        except Exception as e:
            error_str = str(e)
            logger.warning(f"Build attempt {attempt} failed: {error_str[:200]}")

            fixed, fix_description = attempt_fix(error_str, project_dir)

            attempts.append({
                "attempt": attempt,
                "error": error_str[:500],
                "fix_applied": fix_description,
                "success": False
            })

            if not fixed:
                logger.error(f"Could not fix build error: {fix_description}")
                if attempt == max_attempts:
                    return {
                        "success": False,
                        "attempts": attempts,
                        "final_error": error_str
                    }
            else:
                logger.info(f"Fix applied: {fix_description} — retrying build")

    return {
        "success": False,
        "attempts": attempts,
        "final_error": "Max attempts reached"
    }