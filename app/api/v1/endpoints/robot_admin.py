from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppException
from app.core.security import require_roles
from app.models.robot_ws import RobotBestImage, RobotCommand, RobotDeliveryState
from app.schemas.common import SuccessResponse
from app.schemas.robot_ws import (
    RobotCommandCreate, RobotCommandCreated,
    RobotCommandResponse, RobotDeliveryStateResponse,
)
from app.services import robot_ws_service as svc
from app.ws.manager import manager

router = APIRouter(
    prefix="/admin/robots",
    tags=["Admin - Điều khiển Robot (WebSocket)"],
    dependencies=[Depends(require_roles("ADMIN", "STAFF"))],
)


@router.get("", response_model=SuccessResponse[list[RobotDeliveryStateResponse]])
async def list_robots(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(RobotDeliveryState).order_by(RobotDeliveryState.robot_id))).scalars().all()
    online = manager.online_robot_ids()
    data = []
    for r in rows:
        item = RobotDeliveryStateResponse.model_validate(r)
        item.online = r.robot_id in online
        data.append(item)
    return SuccessResponse(data=data)


@router.post("/{robot_id}/commands", response_model=SuccessResponse[RobotCommandCreated])
async def create_robot_command(
    robot_id: str, payload: RobotCommandCreate, db: AsyncSession = Depends(get_db)
):
    cmd = await svc.create_command(db, robot_id, payload.command, payload.payload)
    delivered_live = manager.notify_commands(robot_id)
    return SuccessResponse(
        data=RobotCommandCreated(
            command_id=cmd.command_id, command=cmd.command, delivered_live=delivered_live
        ),
        message="Đã gửi lệnh tới robot" if delivered_live
        else "Robot đang offline, lệnh sẽ gửi khi robot kết nối lại",
    )


@router.get("/{robot_id}/commands", response_model=SuccessResponse[list[RobotCommandResponse]])
async def list_robot_commands(
    robot_id: str, limit: int = Query(default=50, ge=1, le=200), db: AsyncSession = Depends(get_db)
):
    rows = (
        await db.execute(
            select(RobotCommand).where(RobotCommand.robot_id == robot_id)
            .order_by(RobotCommand.created_at.desc()).limit(limit)
        )
    ).scalars().all()
    return SuccessResponse(data=[RobotCommandResponse.model_validate(r) for r in rows])


@router.get("/{robot_id}/images/{task_id}")
async def get_best_image(robot_id: str, task_id: str, db: AsyncSession = Depends(get_db)):
    img = (
        await db.execute(
            select(RobotBestImage).where(
                RobotBestImage.robot_id == robot_id, RobotBestImage.task_id == task_id
            )
        )
    ).scalar_one_or_none()
    if img is None:
        raise AppException(404, "Không tìm thấy ảnh")
    return Response(content=img.image_data, media_type=img.mime_type)