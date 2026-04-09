import json
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from core.utils import get_logger, write_generated_files
from agents.state import AppState
from graph.builder import build_graph
from api.routes import router

load_dotenv()
logger = get_logger("main")

app = FastAPI(
    title="App Builder API",
    description="AI-powered full-stack app generator",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


def run_once(prompt: str):
    """Run the agent pipeline once from terminal — for testing."""
    logger.info(f"Starting app generation for: {prompt}")

    pipeline = build_graph()

    initial_state = AppState(
        user_prompt=prompt,
        client_id=None,
        plan=None,
        frontend_code=None,
        backend_code=None,
        database_code=None,
        devops_code=None,
        review_result=None,
        review_attempts=0,
        approved=None,
        error=None,
        current_stage="starting"
    )

    result = pipeline.invoke(initial_state)

    print(f"\n{'='*60}")
    if result.get("error"):
        print(f"FAILED: {result['error']}")
    else:
        plan = result.get("plan", {})
        review = result.get("review_result", {})

        print(f"APP: {plan.get('app_name')}")
        print(f"STAGE: {result.get('current_stage')}")
        print(f"\nFILES GENERATED:")

        for agent, key in [
            ("Frontend", "frontend_code"),
            ("Backend", "backend_code"),
            ("Database", "database_code"),
            ("DevOps", "devops_code")
        ]:
            files = result.get(key, {})
            if files:
                print(f"\n  {agent}:")
                for path in files.keys():
                    print(f"    {path}")

        write_generated_files(result, output_dir="generated")

        print(f"\nREVIEW: {'PASSED' if review.get('passed') else 'ISSUES FOUND'}")
        print(f"SUMMARY: {review.get('summary', 'N/A')}")
    print(f"{'='*60}\n")

    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        # Start FastAPI server
        logger.info("Starting FastAPI server on http://localhost:8000")
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    else:
        # Run once from terminal
        run_once("Build a minimal task manager with a dark theme, use emerald green as the primary color, clean and focused like Linear")