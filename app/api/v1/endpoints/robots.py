"""HTTP endpoints for Raspberry Pi robot communication."""

from typing import Literal

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppException
from app.core.security import is_valid_device_key
from app.schemas.common import SuccessResponse
from app.schemas.robot_ws import (
    BestImagePayload,
    CurrentTaskPayload,
    DetectionPayload,
    EventPayload,
    StatusPayload,
)
from app.services import robot_ws_service as svc


router = APIRouter(
    prefix="/robots",
    tags=["Robot - Raspberry Pi HTTP"],
)


class RobotCommandAckPayload(BaseModel):
    status: Literal["DONE", "FAILED"]


def require_device_key(
    x_device_key: str = Header(default="", alias="X-Device-Key"),
) -> None:
    if not is_valid_device_key(x_device_key):
        raise AppException(status_code=401, message="Device key không hợp lệ")


def handle_service_error(exc: ValueError) -> None:
    message = str(exc)
    if message in {
        "Không tìm thấy món",
        "Không tìm thấy đơn hàng",
        "Không tìm thấy lệnh",
    }:
        raise AppException(status_code=404, message=message)
    raise AppException(status_code=400, message=message)


@router.post(
    "/{robot_id}/detections",
    dependencies=[Depends(require_device_key)],
)
async def send_detections(
    robot_id: str,
    payload: DetectionPayload,
    db: AsyncSession = Depends(get_db),
):
    try:
        data = await svc.receive_detections(db, robot_id, payload.model_dump())
    except ValueError as exc:
        handle_service_error(exc)
    return SuccessResponse(data=data)


@router.post(
    "/{robot_id}/tasks/current",
    dependencies=[Depends(require_device_key)],
)
async def get_current_task(
    robot_id: str,
    payload: CurrentTaskPayload,
    db: AsyncSession = Depends(get_db),
):
    try:
        data = await svc.get_current_task(db, robot_id, payload.model_dump())
    except ValueError as exc:
        handle_service_error(exc)
    return SuccessResponse(data=data)


@router.post(
    "/{robot_id}/images/best",
    dependencies=[Depends(require_device_key)],
)
async def upload_best_image(
    robot_id: str,
    payload: BestImagePayload,
    db: AsyncSession = Depends(get_db),
):
    try:
        data = await svc.upload_best_image(db, robot_id, payload.model_dump())
    except ValueError as exc:
        handle_service_error(exc)
    return SuccessResponse(data=data)


@router.post(
    "/{robot_id}/events",
    dependencies=[Depends(require_device_key)],
)
async def send_event(
    robot_id: str,
    payload: EventPayload,
    db: AsyncSession = Depends(get_db),
):
    try:
        data = await svc.receive_event(db, robot_id, payload.model_dump())
    except ValueError as exc:
        handle_service_error(exc)
    return SuccessResponse(data=data)


@router.post(
    "/{robot_id}/status",
    dependencies=[Depends(require_device_key)],
)
async def send_status(
    robot_id: str,
    payload: StatusPayload,
    db: AsyncSession = Depends(get_db),
):
    try:
        data = await svc.receive_status(db, robot_id, payload.model_dump())
    except ValueError as exc:
        handle_service_error(exc)
    return SuccessResponse(data=data)


@router.get(
    "/{robot_id}/commands",
    dependencies=[Depends(require_device_key)],
)
async def get_commands(
    robot_id: str,
    db: AsyncSession = Depends(get_db),
):
    commands = await svc.get_pending_commands(db, robot_id)
    return SuccessResponse(data={"commands": commands})


@router.post(
    "/{robot_id}/commands/{command_id}/acknowledge",
    dependencies=[Depends(require_device_key)],
)
async def acknowledge_command(
    robot_id: str,
    command_id: str,
    payload: RobotCommandAckPayload,
    db: AsyncSession = Depends(get_db),
):
    try:
        data = await svc.acknowledge_command(
            db,
            robot_id,
            {"command_id": command_id, "status": payload.status},
        )
    except ValueError as exc:
        handle_service_error(exc)
    return SuccessResponse(data=data)
