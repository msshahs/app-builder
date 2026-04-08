import json
import uuid
from typing import Dict
from fastapi import WebSocket
from core.utils import get_logger

logger = get_logger("websocket")

class ConnectionManager:
    """Manages active WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client connected: {client_id}")
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client disconnected: {client_id}")
    
    async def send(self, client_id: str, message: dict):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(
                    json.dumps(message)
                )
            except Exception as e:
                logger.error(f"Failed to send to {client_id}: {e}")
                self.disconnect(client_id)


manager = ConnectionManager()


async def stream_event(client_id: str, event_type: str, data: dict):
    """Send a structured event to the frontend."""
    await manager.send(client_id, {
        "type": event_type,
        "data": data
    })


async def stream_agent_start(client_id: str, agent: str):
    await stream_event(client_id, "agent_start", {"agent": agent})


async def stream_agent_complete(client_id: str, agent: str, files: list):
    await stream_event(client_id, "agent_complete", {
        "agent": agent,
        "files": files
    })


async def stream_agent_error(client_id: str, agent: str, error: str):
    await stream_event(client_id, "agent_error", {
        "agent": agent,
        "error": error
    })


async def stream_review_result(client_id: str, passed: bool, issues: list):
    await stream_event(client_id, "review_result", {
        "passed": passed,
        "issues": issues
    })


async def stream_complete(client_id: str, files: dict):
    await stream_event(client_id, "generation_complete", {
        "total_files": sum(
            len(v) for v in files.values() if isinstance(v, list)
        ),
        "file_tree": {
            "frontend": files.get("frontend", []),
            "backend":  files.get("backend", []),
            "database": files.get("database", []),
            "devops":   files.get("devops", []),
        },
        "all_files": files.get("all_files", {}),
        "project_id": files.get("project_id", "")
    })

async def stream_error(client_id: str, error: str):
    await stream_event(client_id, "fatal_error", {"error": error})