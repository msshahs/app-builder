import os
import shutil
from core.utils import get_logger

logger = get_logger("template_engine")

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")


def apply_backend_templates(output_dir: str):
    """Copy fixed backend templates into the generated project."""
    backend_template = os.path.join(TEMPLATES_DIR, "backend")
    backend_output = os.path.join(output_dir, "backend")

    os.makedirs(backend_output, exist_ok=True)

    # Copy fixed files
    fixed_files = [
        "package.json",
        "src/server.js",
        "src/middleware/auth.js",
        "src/middleware/errorHandler.js",
        "src/models/User.js",
        "src/routes/auth.js",
    ]

    for file_path in fixed_files:
        src = os.path.join(backend_template, file_path.replace("src/", ""))
        dst = os.path.join(backend_output, "src", file_path.replace("src/", ""))

        os.makedirs(os.path.dirname(dst), exist_ok=True)

        if os.path.exists(src):
            shutil.copy2(src, dst)
            logger.info(f"Template applied: {file_path}")

    logger.info("Backend templates applied")


def apply_frontend_templates(output_dir: str):
    """Copy fixed frontend templates into the generated project."""
    frontend_template = os.path.join(TEMPLATES_DIR, "frontend")
    frontend_output = os.path.join(output_dir, "frontend")

    os.makedirs(frontend_output, exist_ok=True)

    fixed_files = [
        "package.json",
        "src/utils/api.js",
        "src/utils/tokenStorage.js",
        "src/hooks/useAuth.js",
    ]

    for file_path in fixed_files:
        src = os.path.join(frontend_template, file_path)
        dst = os.path.join(frontend_output, file_path)

        os.makedirs(os.path.dirname(dst), exist_ok=True)

        if os.path.exists(src):
            shutil.copy2(src, dst)
            logger.info(f"Template applied: {file_path}")

    logger.info("Frontend templates applied")


def apply_all_templates(output_dir: str):
    """Apply all templates to a generated project."""
    apply_backend_templates(output_dir)
    apply_frontend_templates(output_dir)
    logger.info(f"All templates applied to: {output_dir}")