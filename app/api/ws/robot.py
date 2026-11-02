import asyncio
import json
import logging

from fastapi import APIRouter, Header, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import is_valid_device_key
from app.services import robot_ws_service as svc
from app.ws.manager import manager

router = APIRouter(tags=["Robot WebSocket"])
logger = logging.getLogger("robot_backend.ws")


async def _push_commands(websocket: WebSocket, robot_id: str) -> None:
    sent: set[str] = set()
    while True:
        try:
            async with AsyncSessionLocal() as db:   # session ngắn, không giữ pool
                commands = await svc.get_pending_commands(db, robot_id)
            for command in commands:
                if command["command_id"] not in sent:
                    await manager.send_json(websocket, {"type": "command", "data": command})
                    sent.add(command["command_id"])
            sent &= {c["command_id"] for c in commands}
        except (WebSocketDisconnect, RuntimeError):
            return
        except Exception:
            logger.exception("Không thể gửi lệnh tới robot %s", robot_id)
        await manager.wait_for_wakeup(websocket, settings.ROBOT_COMMAND_FALLBACK_POLL_SECONDS)


@router.websocket("/ws/robot/{robot_id}")
async def robot_websocket(
    websocket: WebSocket,
    robot_id: str,
    x_device_key: str = Header(default="", alias="X-Device-Key"),
):
    if not is_valid_device_key(x_device_key):
        await websocket.accept()
        await websocket.close(code=1008, reason="Device key không hợp lệ")
        return

    await manager.connect(websocket, robot_id)
    logger.info("Robot %s đã kết nối WebSocket", robot_id)
    command_task = asyncio.create_task(_push_commands(websocket, robot_id))

    try:
        while True:
            request_id = None
            try:
                message = json.loads(await websocket.receive_text())
                if not isinstance(message, dict):
                    raise ValueError("Message phải là JSON object")
                request_id = message.get("id")
                action = message.get("action")
                payload = message.get("payload", {})
                if not isinstance(request_id, str) or not request_id:
                    raise ValueError("Message cần có id dạng chuỗi")
                if not isinstance(action, str) or not isinstance(payload, dict):
                    raise ValueError("Message cần có action và payload hợp lệ")

                async with AsyncSessionLocal() as db:   # 1 session / 1 message
                    try:
                        result = await svc.dispatch_action(db, robot_id, action, payload)
                    except Exception:
                        await db.rollback()
                        raise
                response = {"id": request_id, "ok": True, "data": result}
            except (json.JSONDecodeError, ValueError, ValidationError) as exc:
                response = {"id": request_id, "ok": False, "error": str(exc)}
            except (WebSocketDisconnect, RuntimeError):
                raise
            except Exception:
                logger.exception("Lỗi xử lý WebSocket request cho robot %s", robot_id)
                response = {"id": request_id, "ok": False, "error": "Lỗi xử lý yêu cầu trên server"}
            await manager.send_json(websocket, response)
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        command_task.cancel()
        await asyncio.gather(command_task, return_exceptions=True)
        manager.disconnect(websocket, robot_id)
        logger.info("Robot %s đã ngắt kết nối", robot_id)