import asyncio
import base64
import binascii
import json
import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.dish import Dish
from app.models.order import Order, OrderDetail
from app.models.robot_ws import (
    RobotBestImage, RobotCommand, RobotDeliveryState, RobotDetection, RobotEvent,
)
from app.models.table import Table
from app.schemas.robot_ws import (
    AckPayload, BestImagePayload, CurrentTaskPayload,
    DetectionPayload, EventPayload, StatusPayload,
)

# SQL dump dùng PROCESSING, enum OrderStatus của app dùng PREPARING -> nhận cả hai
ACTIVE_ORDER_STATUSES = ("PENDING", "PREPARING", "PROCESSING", "DELIVERING")


def _dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


def delivery_destination(row) -> dict:
    if not row:
        return {"has_task": False, "table_number": None, "order_id": None}
    return {"has_task": True, "table_number": int(row.table_number), "order_id": row.order_id}


async def earliest_delivery_for_label(db: AsyncSession, ai_label: str):
    stmt = (
        select(Table.table_number, Order.order_id)
        .select_from(Dish)
        .join(OrderDetail, OrderDetail.dish_id == Dish.dish_id)
        .join(Order, Order.order_id == OrderDetail.order_id)
        .join(Table, Table.table_id == Order.table_id)
        .where(
            Dish.ai_label_id == ai_label,
            Order.order_status.in_(ACTIVE_ORDER_STATUSES),
            OrderDetail.served_status.is_(False),
        )
        .order_by(Order.created_at.asc(), Table.table_number.asc())
        .limit(1)
    )
    return (await db.execute(stmt)).first()


async def receive_detections(db: AsyncSession, robot_id: str, data: dict) -> dict:
    body = DetectionPayload.model_validate(data)
    db.add_all(
        RobotDetection(
            detection_id=str(uuid.uuid4()),
            robot_id=robot_id,
            task_id=body.task_id,
            label=det.label,
            confidence=det.confidence,
            quantity=det.quantity,
            table_number=body.table_number,
        )
        for det in body.detections
    )
    await db.commit()

    matched: dict[str, dict] = {}
    first_dest = None
    for det in body.detections:
        dest = delivery_destination(await earliest_delivery_for_label(db, det.label))
        matched[det.label] = dest
        if dest["has_task"] and first_dest is None:
            first_dest = dest

    payload = first_dest or delivery_destination(None)
    return {
        "ok": True,
        "has_task": payload["has_task"],
        "table_number": payload["table_number"],
        "order_id": payload["order_id"],
        "matched_tables": matched,
    }


async def get_current_task(db: AsyncSession, robot_id: str, data: dict) -> dict:
    body = CurrentTaskPayload.model_validate(data)
    label = body.label
    if not label:
        stmt = select(RobotDetection.label).where(RobotDetection.robot_id == robot_id)
        if body.task_id:
            stmt = stmt.where(RobotDetection.task_id == body.task_id)
        stmt = stmt.order_by(RobotDetection.created_at.desc()).limit(1)
        label = (await db.execute(stmt)).scalar_one_or_none()
    if not label:
        return delivery_destination(None)
    return delivery_destination(await earliest_delivery_for_label(db, label))


async def upload_best_image(db: AsyncSession, robot_id: str, data: dict) -> dict:
    body = BestImagePayload.model_validate(data)
    if not body.content_type.startswith("image/"):
        raise ValueError("Chỉ chấp nhận file ảnh")

    def _decode() -> bytes:
        return base64.b64decode(body.image_base64, validate=True)

    try:
        raw = await asyncio.to_thread(_decode)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("image_base64 không hợp lệ") from exc
    if not raw:
        raise ValueError("Ảnh rỗng")
    if len(raw) > settings.ROBOT_MAX_IMAGE_BYTES:
        raise ValueError(f"Ảnh vượt quá {settings.ROBOT_MAX_IMAGE_BYTES // (1024 * 1024)} MB")

    old = (
        await db.execute(
            select(RobotBestImage.best_confidence)
            .where(RobotBestImage.robot_id == robot_id, RobotBestImage.task_id == body.task_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if old is not None and body.confidence <= float(old):
        await db.rollback()
        return {"ok": True, "saved": False, "reason": "confidence_not_higher",
                "best_confidence": float(old)}

    image_id = str(uuid.uuid4())
    stmt = mysql_insert(RobotBestImage).values(
        image_id=image_id, robot_id=robot_id, task_id=body.task_id,
        best_confidence=body.confidence, table_number=body.table_number,
        detections_json=_dumps(body.detections), mime_type=body.content_type,
        image_data=raw, updated_at=func.now(),
    )
    stmt = stmt.on_duplicate_key_update(
        image_id=stmt.inserted.image_id,
        best_confidence=stmt.inserted.best_confidence,
        table_number=stmt.inserted.table_number,
        detections_json=stmt.inserted.detections_json,
        mime_type=stmt.inserted.mime_type,
        image_data=stmt.inserted.image_data,
        updated_at=func.now(),
    )
    await db.execute(stmt)
    await db.commit()
    return {"ok": True, "saved": True, "image_id": image_id, "best_confidence": body.confidence}


async def receive_event(db: AsyncSession, robot_id: str, data: dict) -> dict:
    body = EventPayload.model_validate(data)
    db.add(RobotEvent(
        event_id=str(uuid.uuid4()), robot_id=robot_id, event_type=body.event_type,
        severity=body.severity, message=body.message, metadata_json=_dumps(body.metadata),
    ))
    await db.commit()
    return {"ok": True}


async def _upsert_state(db: AsyncSession, **values) -> None:
    stmt = mysql_insert(RobotDeliveryState).values(**values, updated_at=func.now())
    update_cols = {k: stmt.inserted[k] for k in values if k != "robot_id"}
    await db.execute(stmt.on_duplicate_key_update(**update_cols, updated_at=func.now()))


async def receive_status(db: AsyncSession, robot_id: str, data: dict) -> dict:
    body = StatusPayload.model_validate(data)
    await _upsert_state(
        db, robot_id=robot_id, delivery_status=body.delivery_status,
        table_number=body.table_number, order_id=body.order_id,
        battery_percent=body.battery_percent, obstacle_detected=body.obstacle_detected,
        metadata_json=_dumps(body.metadata),
    )
    await db.commit()
    return {"ok": True, "robot_id": robot_id, "status": body.delivery_status}


async def get_pending_commands(db: AsyncSession, robot_id: str) -> list[dict]:
    rows = (
        await db.execute(
            select(RobotCommand)
            .where(RobotCommand.robot_id == robot_id, RobotCommand.command_status == "PENDING")
            .order_by(RobotCommand.created_at.asc())
            .limit(20)
        )
    ).scalars().all()
    return [
        {
            "command_id": r.command_id,
            "command": r.command,
            "payload": json.loads(r.payload_json or "{}"),
            "created_at": str(r.created_at),
        }
        for r in rows
    ]


async def acknowledge_command(db: AsyncSession, robot_id: str, data: dict) -> dict:
    body = AckPayload.model_validate(data)
    cmd = (
        await db.execute(
            select(RobotCommand).where(
                RobotCommand.command_id == body.command_id, RobotCommand.robot_id == robot_id
            )
        )
    ).scalar_one_or_none()
    if cmd is None:
        raise ValueError("Không tìm thấy lệnh")

    cmd.command_status = body.status
    cmd.result_json = _dumps({"status": body.status, "message": body.message})
    cmd.completed_at = datetime.now()

    if cmd.command == "RESET_STATUS" and body.status == "DONE":
        await _upsert_state(
            db, robot_id=robot_id, delivery_status="NOT_DELIVERED", table_number=None,
            order_id=None, battery_percent=None, obstacle_detected=False, metadata_json="{}",
        )
    await db.commit()
    return {"ok": True}


async def create_command(db: AsyncSession, robot_id: str, command: str, payload: dict) -> RobotCommand:
    cmd = RobotCommand(
        command_id=str(uuid.uuid4()), robot_id=robot_id, command=command,
        payload_json=_dumps(payload), command_status="PENDING",
    )
    db.add(cmd)
    await db.commit()
    return cmd


async def dispatch_action(db: AsyncSession, robot_id: str, action: str, data: dict) -> dict:
    if action == "send_detections":
        return await receive_detections(db, robot_id, data)
    if action == "get_current_task":
        return await get_current_task(db, robot_id, data)
    if action == "upload_best_image":
        return await upload_best_image(db, robot_id, data)
    if action == "send_event":
        return await receive_event(db, robot_id, data)
    if action == "send_status":
        return await receive_status(db, robot_id, data)
    if action == "get_commands":
        return {"commands": await get_pending_commands(db, robot_id)}
    if action == "acknowledge_command":
        return await acknowledge_command(db, robot_id, data)
    raise ValueError(f"Action không được hỗ trợ: {action}")