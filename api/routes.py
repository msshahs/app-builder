import uuid
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from core.utils import get_logger, write_generated_files
from agents.state import AppState
from graph.builder import build_graph
from api.websocket import manager, stream_complete, stream_error
from deploy.pipeline import deploy_generated_app

logger = get_logger("api")
router = APIRouter()


class GenerateRequest(BaseModel):
    prompt: str


@router.get("/health")
async def health():
    return {"status": "ok", "service": "app-builder"}


@router.post("/generate")
async def generate(request: GenerateRequest):
    """
    Trigger app generation without WebSocket.
    Returns project_id for polling.
    """
    project_id = str(uuid.uuid4())[:8]
    return {
        "project_id": project_id,
        "message": "Use WebSocket endpoint for real-time streaming"
    }


@router.post("/deploy/{project_id}")
async def deploy_project(project_id: str):
    """Deploy a generated project to AWS ECS."""
    import os
    project_dir = f"projects/{project_id}"

    if not os.path.exists(project_dir):
        return JSONResponse({"error": "Project not found"}, status_code=404)

    result = await deploy_generated_app(project_id, project_dir)
    return result

@router.get("/files/{project_id}")
async def get_project_files(project_id: str):
    """Return all generated file contents for a project."""
    import os
    project_dir = f"projects/{project_id}"
    
    if not os.path.exists(project_dir):
        return JSONResponse({"error": "Project not found"}, status_code=404)
    
    files = {}
    for root, dirs, filenames in os.walk(project_dir):
        for filename in filenames:
            full_path = os.path.join(root, filename)
            relative_path = os.path.relpath(full_path, project_dir)
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    files[relative_path] = f.read()
            except Exception:
                files[relative_path] = "// Could not read file"
    
    return {"project_id": project_id, "files": files}


@router.websocket("/ws/deploy/{project_id}/{client_id}")
async def websocket_deploy(websocket: WebSocket, project_id: str, client_id: str):
    """WebSocket endpoint for real-time deployment streaming."""
    await manager.connect(websocket, client_id)

    try:
        import os
        project_dir = f"projects/{project_id}"

        if not os.path.exists(project_dir):
            await stream_error(client_id, "Project not found")
            return

        async def stream_update(message: str, step: str):
            await manager.send(client_id, {
                "type": "deploy_update",
                "data": {"message": message, "step": step}
            })

        result = await deploy_generated_app(
            project_id, project_dir, stream_update
        )

        await manager.send(client_id, {
            "type": "deploy_complete",
            "data": result
        })

    except WebSocketDisconnect:
        logger.info(f"Deploy client {client_id} disconnected")
    except Exception as e:
        await stream_error(client_id, str(e))
    finally:
        manager.disconnect(client_id)

@router.websocket("/ws/{client_id}")
async def websocket_generate(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint for real-time agent streaming.
    Client connects, sends prompt, receives agent events as they happen.
    """
    await manager.connect(websocket, client_id)

    try:
        # Wait for the prompt from client
        data = await websocket.receive_json()
        prompt = data.get("prompt", "").strip()

        if not prompt:
            await stream_error(client_id, "Prompt cannot be empty")
            return

        logger.info(f"Generation started for client {client_id}: {prompt}")

        # Build and run the graph in a thread
        # (LangGraph is sync, FastAPI is async — run in executor)
        loop = asyncio.get_event_loop()

        initial_state = AppState(
            user_prompt=prompt,
            client_id=client_id,
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

        app = build_graph()

        result = await loop.run_in_executor(
            None,
            lambda: app.invoke(initial_state)
        )

        if result.get("error"):
            await stream_error(client_id, result["error"])
            return

        # Write files to disk
        project_id = str(uuid.uuid4())[:8]
        output_dir = f"projects/{project_id}"
        write_generated_files(result, output_dir=output_dir)

        # Send completion event with full file tree
        await stream_complete(client_id, {
            "frontend": list((result.get("frontend_code") or {}).keys()),
            "backend": list((result.get("backend_code") or {}).keys()),
            "database": list((result.get("database_code") or {}).keys()),
            "devops": list((result.get("devops_code") or {}).keys()),
            "project_id": project_id,
            "all_files": {
                **( result.get("frontend_code") or {}),
                **( result.get("backend_code") or {}),
                **( result.get("database_code") or {}),
                **( result.get("devops_code") or {}),
            }
        })

        logger.info(f"Generation complete for client {client_id} → {output_dir}")

    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"Error for client {client_id}: {e}")
        await stream_error(client_id, str(e))
    finally:
        manager.disconnect(client_id)