import os
import secrets
import asyncio
from core.utils import get_logger
from deploy.mongodb import provision_app_database
from deploy.docker_builder import ecr_login, build_and_push_frontend, build_and_push_backend
from deploy.ecs_deployer import deploy_app
from agents.alignment import run_alignment
from agents.build_fixer import attempt_fix
from agents.runtime_monitor import monitor_deployment
from agents.code_intelligence import run_code_intelligence

logger = get_logger("pipeline")


def build_backend_with_healing(project_id, project_dir, env_vars, max_attempts=3):
    """Build backend with automatic error fixing."""
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"Backend build attempt {attempt}/{max_attempts}")
            image = build_and_push_backend(project_id, project_dir, env_vars)
            logger.info(f"Backend build succeeded on attempt {attempt}")
            return image
        except Exception as e:
            error_str = str(e)
            logger.warning(f"Backend build failed: {error_str[:300]}")
            if attempt == max_attempts:
                raise
            fixed, description = attempt_fix(error_str, project_dir)
            if fixed:
                logger.info(f"Applied fix: {description} — retrying")
            else:
                logger.error(f"No fix available: {description}")
                raise


def build_frontend_with_healing(project_id, project_dir, backend_url, max_attempts=3):
    """Build frontend with automatic error fixing."""
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"Frontend build attempt {attempt}/{max_attempts}")
            image = build_and_push_frontend(project_id, project_dir, backend_url)
            logger.info(f"Frontend build succeeded on attempt {attempt}")
            return image
        except Exception as e:
            error_str = str(e)
            logger.warning(f"Frontend build failed: {error_str[:300]}")
            if attempt == max_attempts:
                raise
            fixed, description = attempt_fix(error_str, project_dir)
            if fixed:
                logger.info(f"Applied fix: {description} — retrying")
            else:
                logger.error(f"No fix available: {description}")
                raise


async def deploy_generated_app(
    project_id: str,
    project_dir: str,
    stream_update=None,
    spec: dict = None
) -> dict:
    """
    Full self-healing deployment pipeline:
    1. Code alignment — fix all known issues before build
    2. Provision MongoDB
    3. Build backend with auto-healing
    4. Build frontend with auto-healing
    5. Deploy to ECS
    6. Monitor runtime — fix and redeploy if needed
    7. Smoke test — verify auth works end to end
    8. Return live URL
    """
    
        # Load spec from plan file if not passed
    if not spec:
        import json
        plan_path = os.path.join(project_dir, ".plan.json")
        if os.path.exists(plan_path):
            with open(plan_path, "r") as f:
                spec = json.load(f)
            logger.info("Loaded spec from .plan.json")

    async def update(message: str, step: str = "info"):
        logger.info(message)
        if stream_update:
            await stream_update(message, step)

    try:
        # Step 1 — Code Alignment (runs before anything else)
        if spec:
            await update("Running code alignment checks...", "align_start")
            alignment_result = run_alignment(project_dir, spec)
            fixed_count = alignment_result["issues_fixed"]
            if fixed_count > 0:
                await update(
                    f"Alignment fixed {fixed_count} issues: {', '.join(alignment_result['details'][:3])}",
                    "align_complete"
                )
            else:
                await update("Code alignment passed — no issues found", "align_complete")

        if spec:
            await update("Running code intelligence review...", "intelligence_start")
            intelligence_result = run_code_intelligence(project_dir, spec)
            fixed_count = len(intelligence_result.get("files_fixed", []))
            issues_count = len(intelligence_result.get("issues_found", []))
            if fixed_count > 0:
                await update(
                    f"Code intelligence fixed {fixed_count} files, found {issues_count} issues",
                    "intelligence_complete"
                )
            else:
                await update("Code intelligence: all files look good", "intelligence_complete")
        
        # Step 2 — MongoDB
        await update("Provisioning database...", "deploy_start")
        db_info = provision_app_database(project_id)
        mongo_uri = db_info["mongo_uri"]
        await update(f"Database ready: {db_info['db_name']}", "deploy_progress")

        # Step 3 — Generate secrets
        jwt_secret = secrets.token_hex(32)
        await update("Environment variables generated", "deploy_progress")

        # Step 4 — ECR login
        await update("Authenticating with AWS ECR...", "deploy_progress")
        ecr_login()

        # Step 5 — Build backend with healing
        await update("Building backend Docker image...", "deploy_progress")
        backend_image = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: build_backend_with_healing(
                project_id, project_dir,
                {
                    "MONGO_URI": mongo_uri,
                    "JWT_SECRET": jwt_secret,
                    "PORT": "5000",
                    "NODE_ENV": "production"
                }
            )
        )
        await update("Backend image pushed to ECR", "deploy_progress")

        # Step 6 — Build frontend with healing
        await update("Building frontend Docker image...", "deploy_progress")
        frontend_image = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: build_frontend_with_healing(
                project_id, project_dir, "/api"
            )
        )
        await update("Frontend image pushed to ECR", "deploy_progress")

        # Step 7 — Deploy to ECS
        await update("Deploying to AWS ECS Fargate...", "deploy_progress")
        deploy_result = deploy_app(
            project_id=project_id,
            frontend_image=frontend_image,
            backend_image=backend_image,
            mongo_uri=mongo_uri,
            jwt_secret=jwt_secret
        )
        alb_dns = deploy_result["alb_dns"]
        await update(f"Containers starting — {deploy_result['frontend_url']}", "deploy_progress")

        # Step 8 — Runtime monitoring + smoke test
        await update("Monitoring deployment health...", "monitor_start")
        monitor_result = await monitor_deployment(project_id, alb_dns)

        if monitor_result.get("healthy"):
            if monitor_result.get("auth_working"):
                await update("Smoke tests passed — auth working end to end ✅", "monitor_complete")
            else:
                await update("App is live — auth smoke test had issues", "monitor_complete")
        else:
            await update(
                f"Warning: deployment health check failed — {monitor_result.get('error', 'unknown')}",
                "monitor_warning"
            )

        await update(
            f"Deployment complete — {deploy_result['frontend_url']}",
            "deploy_complete"
        )

        return {
            "success": True,
            "frontend_url": deploy_result["frontend_url"],
            "backend_url": deploy_result["backend_url"],
            "project_id": project_id,
            "alb_dns": alb_dns,
            "health": monitor_result,
            "alignment_fixes": alignment_result.get("details", []) if spec else []
        }

    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        await update(f"Deployment failed: {str(e)}", "deploy_error")
        return {
            "success": False,
            "error": str(e),
            "project_id": project_id
        }