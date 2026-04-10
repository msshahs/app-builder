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

    # package.json goes to backend/ root (NOT backend/src/)
    pkg_src = os.path.join(backend_template, "package.json")
    pkg_dst = os.path.join(backend_output, "package.json")
    if os.path.exists(pkg_src):
        shutil.copy2(pkg_src, pkg_dst)
        logger.info("Template applied: package.json")

    # src/* files go to backend/src/
    src_files = [
        "server.js",
        "middleware/auth.js",
        "middleware/errorHandler.js",
        "models/User.js",
        "routes/auth.js",
    ]
    for file_path in src_files:
        src = os.path.join(backend_template, file_path)
        dst = os.path.join(backend_output, "src", file_path)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            logger.info(f"Template applied: src/{file_path}")

    logger.info("Backend templates applied")


def apply_frontend_templates(output_dir: str):
    """Copy fixed frontend templates into the generated project."""
    frontend_template = os.path.join(TEMPLATES_DIR, "frontend")
    frontend_output = os.path.join(output_dir, "frontend")
    os.makedirs(frontend_output, exist_ok=True)

    # All template files to copy (relative to templates/frontend/)
    all_files = [
        # Root config files
        "package.json",
        "vite.config.js",
        "index.html",
        "tailwind.config.js",
        "postcss.config.js",
        # src files
        "src/main.jsx",
        "src/index.css",
        "src/utils/api.js",
        "src/utils/tokenStorage.js",
        "src/hooks/useAuth.js",
    ]

    for file_path in all_files:
        src = os.path.join(frontend_template, file_path)
        dst = os.path.join(frontend_output, file_path)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            logger.info(f"Template applied: {file_path}")

    logger.info("Frontend templates applied")


def fix_misplaced_frontend_files(output_dir: str):
    """Move files from generated/src/ to generated/frontend/src/ if agent forgot the prefix."""
    import shutil
    wrong_src = os.path.join(output_dir, "src")
    correct_src = os.path.join(output_dir, "frontend", "src")

    if os.path.exists(wrong_src):
        logger.info("Fixing misplaced frontend files — moving src/ to frontend/src/")
        os.makedirs(correct_src, exist_ok=True)

        for root, dirs, files in os.walk(wrong_src):
            for file in files:
                src_path = os.path.join(root, file)
                rel_path = os.path.relpath(src_path, wrong_src)
                dst_path = os.path.join(correct_src, rel_path)
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                shutil.move(src_path, dst_path)
                logger.info(f"Moved: src/{rel_path} → frontend/src/{rel_path}")

        shutil.rmtree(wrong_src)
        logger.info("Cleanup complete — all frontend files in correct location")


def apply_all_templates(output_dir: str):
    """Apply all templates to a generated project."""
    fix_misplaced_frontend_files(output_dir)
    apply_backend_templates(output_dir)
    apply_frontend_templates(output_dir)
    logger.info(f"All templates applied to: {output_dir}")