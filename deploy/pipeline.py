import os
import secrets
from core.utils import get_logger
from deploy.mongodb import provision_app_database
from deploy.docker_builder import ecr_login, build_and_push_frontend, build_and_push_backend
from deploy.ecs_deployer import deploy_app

logger = get_logger("pipeline")


async def deploy_generated_app(
    project_id: str,
    project_dir: str,
    stream_update=None
) -> dict:
    """
    Full deployment pipeline:
    1. Provision MongoDB database
    2. Build Docker images
    3. Push to ECR
    4. Deploy to ECS
    5. Return live URLs
    """

    async def update(message: str, step: str = "info"):
        logger.info(message)
        if stream_update:
            await stream_update(message, step)

    try:
        # Step 1 — MongoDB
        await update("Provisioning database...", "deploy_start")
        db_info = provision_app_database(project_id)
        mongo_uri = db_info["mongo_uri"]
        await update(f"Database ready: {db_info['db_name']}", "deploy_progress")

        # Step 2 — Generate secrets
        jwt_secret = secrets.token_hex(32)
        await update("Environment variables generated", "deploy_progress")

        # Step 3 — ECR login
        await update("Authenticating with AWS ECR...", "deploy_progress")
        ecr_login()

        # Step 4 — Build backend first (frontend needs backend URL)
        await update("Building backend Docker image...", "deploy_progress")
        backend_image = build_and_push_backend(
            project_id,
            project_dir,
            {
                "MONGO_URI": mongo_uri,
                "JWT_SECRET": jwt_secret,
                "PORT": "5000",
                "NODE_ENV": "production"
            }
        )
        await update("Backend image pushed to ECR", "deploy_progress")

        # Step 5 — Build frontend
        await update("Building frontend Docker image...", "deploy_progress")

        # Placeholder backend URL — will be updated after ALB is created
        frontend_image = build_and_push_frontend(
            project_id,
            project_dir,
            backend_url="/api"
        )
        await update("Frontend image pushed to ECR", "deploy_progress")

        # Step 6 — Deploy to ECS
        await update("Deploying to AWS ECS Fargate...", "deploy_progress")
        deploy_result = deploy_app(
            project_id=project_id,
            frontend_image=frontend_image,
            backend_image=backend_image,
            mongo_uri=mongo_uri,
            jwt_secret=jwt_secret
        )

        await update(
            f"Deployment complete — {deploy_result['frontend_url']}",
            "deploy_complete"
        )

        return {
            "success": True,
            "frontend_url": deploy_result["frontend_url"],
            "backend_url": deploy_result["backend_url"],
            "project_id": project_id
        }

    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        await update(f"Deployment failed: {str(e)}", "deploy_error")
        return {
            "success": False,
            "error": str(e),
            "project_id": project_id
        }