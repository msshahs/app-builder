import asyncio
import aiohttp
import boto3
import re
from datetime import datetime, timedelta
from core.utils import get_logger

logger = get_logger("runtime_monitor")

AWS_REGION = "us-west-2"

RUNTIME_ERROR_PATTERNS = [
    {
        "pattern": r"Cannot find module '([^']+)'",
        "fix": "missing_module",
        "description": "Missing Node.js module"
    },
    {
        "pattern": r"MongooseServerSelectionError|MongoNetworkError",
        "fix": "mongo_connection",
        "description": "MongoDB connection failed"
    },
    {
        "pattern": r"JsonWebTokenError|TokenExpiredError",
        "fix": "jwt_error",
        "description": "JWT configuration error"
    },
    {
        "pattern": r"EADDRINUSE.*(\d+)",
        "fix": "port_conflict",
        "description": "Port already in use"
    },
    {
        "pattern": r"SyntaxError: (.*)",
        "fix": "syntax_error",
        "description": "JavaScript syntax error"
    }
]


async def get_cloudwatch_logs(
    project_id: str,
    service: str = "backend",
    minutes: int = 3
) -> str:
    """Read CloudWatch logs for a service."""
    try:
        logs_client = boto3.client("logs", region_name=AWS_REGION)
        log_group = f"/ecs/app-builder-{project_id}"

        # Get log streams
        streams = logs_client.describe_log_streams(
            logGroupName=log_group,
            logStreamNamePrefix=f"{service}/{service}/",
            orderBy="LastEventTime",
            descending=True,
            limit=3
        )

        if not streams.get("logStreams"):
            return ""

        all_messages = []
        cutoff_time = int((datetime.utcnow() - timedelta(minutes=minutes)).timestamp() * 1000)

        for stream in streams["logStreams"][:2]:
            events = logs_client.get_log_events(
                logGroupName=log_group,
                logStreamName=stream["logStreamName"],
                startTime=cutoff_time,
                limit=100
            )
            for event in events.get("events", []):
                all_messages.append(event["message"])

        return "\n".join(all_messages)

    except Exception as e:
        logger.warning(f"Could not read CloudWatch logs: {e}")
        return ""


async def check_health(alb_dns: str, timeout: int = 10) -> bool:
    """Check if the backend health endpoint returns 200."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"http://{alb_dns}/health",
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                return response.status == 200
    except Exception as e:
        logger.debug(f"Health check failed: {e}")
        return False


async def check_auth_working(alb_dns: str) -> dict:
    """Test auth endpoints are working."""
    results = {}
    import random
    test_email = f"smoke_test_{random.randint(1000, 9999)}@test.com"

    try:
        async with aiohttp.ClientSession() as session:
            # Test register
            async with session.post(
                f"http://{alb_dns}/auth/register",
                json={"name": "Smoke Test", "email": test_email, "password": "Test1234!"},
                timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                data = await response.json()
                results["register"] = {
                    "status": response.status,
                    "has_token": "token" in data,
                    "passed": response.status == 201 and "token" in data
                }

            # Test login with same credentials
            if results["register"]["passed"]:
                async with session.post(
                    f"http://{alb_dns}/auth/login",
                    json={"email": test_email, "password": "Test1234!"},
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    data = await response.json()
                    results["login"] = {
                        "status": response.status,
                        "has_token": "token" in data,
                        "passed": response.status == 200 and "token" in data
                    }
    except Exception as e:
        logger.error(f"Smoke test failed: {e}")
        results["error"] = str(e)

    return results


async def monitor_deployment(
    project_id: str,
    alb_dns: str,
    max_wait_minutes: int = 5
) -> dict:
    """Monitor deployment health and return status."""
    logger.info(f"Monitoring deployment: {project_id}")

    # Wait for initial startup
    logger.info("Waiting 90s for containers to start...")
    await asyncio.sleep(90)

    # Check health with retries
    for attempt in range(10):
        healthy = await check_health(alb_dns)
        if healthy:
            logger.info(f"Health check passed on attempt {attempt + 1}")
            break
        logger.debug(f"Health check attempt {attempt + 1}/10 failed, waiting 20s...")
        await asyncio.sleep(20)
    else:
        # Check logs for errors
        logs = await get_cloudwatch_logs(project_id, "backend", 5)
        return {
            "healthy": False,
            "error": "Health check failed after 5 minutes",
            "logs": logs[:2000]
        }

    # Run smoke tests
    logger.info("Running smoke tests...")
    smoke_results = await check_auth_working(alb_dns)

    register_passed = smoke_results.get("register", {}).get("passed", False)
    login_passed = smoke_results.get("login", {}).get("passed", False)

    return {
        "healthy": True,
        "health_check": True,
        "smoke_tests": smoke_results,
        "auth_working": register_passed and login_passed,
        "ready": True
    }