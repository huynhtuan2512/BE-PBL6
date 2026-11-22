import asyncio
import base64
import binascii
import json
import uuid
from datetime import datetime

from sqlalchemy import exists, func, select, update
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.dish import Dish
from app.models.order import Order, OrderDetail
from app.models.robot_ws import (
    RobotBestImage,
    RobotCommand,
    RobotDeliveryState,
    RobotDetection,
    RobotEvent,
    RobotTask,
)
from app.models.table import Table
from app.schemas.robot_ws import (
    AckPayload,
    BestImagePayload,
    CurrentTaskPayload,
    DetectionPayload,
    EventPayload,
    StatusPayload,
)

ACTIVE_ORDER_STATUSES = ("PENDING", "PREPARING", "PROCESSING")


def _dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def delivery_destination(row) -> dict:
    if row is None:
        return {"has_task": False, "table_number": None, "order_id": None}
    if isinstance(row, tuple):
        table_number, order_id = row
    else:
        table_number, order_id = row.table_number, row.order_id
    return {"has_task": True, "table_number": int(table_number), "order_id": order_id}


async def _dish_exists(db: AsyncSession, dish_id: int) -> bool:
    return (await db.execute(select(exists().where(Dish.dish_id == dish_id)))).scalar()


async def _candidate_for_dish(db: AsyncSession, dish_id: int):
    task_for_detail = exists().where(RobotTask.detail_id == OrderDetail.detail_id)
    result = await db.execute(
        select(OrderDetail.detail_id, Order.order_id, Table.table_number)
        .join(Order, Order.order_id == OrderDetail.order_id)
        .join(Table, Table.table_id == Order.table_id)
        .where(
            OrderDetail.dish_id == dish_id,
            OrderDetail.served_status.is_(False),
            Order.order_status.in_(ACTIVE_ORDER_STATUSES),
            ~task_for_detail,
        )
        .order_by(Order.created_at.asc(), Table.table_number.asc(), OrderDetail.detail_id.asc())
        .with_for_update()
        .limit(1)
    )
    return result.first()


async def _assign(db: AsyncSession, task: RobotTask) -> None:
    if task.detail_id is not None or task.dish_id is None:
        return
    for _ in range(3):
        candidate = await _candidate_for_dish(db, task.dish_id)
        if candidate is None:
            return
        try:
            async with db.begin_nested():
                task.detail_id = candidate.detail_id
                task.order_id = candidate.order_id
                task.table_number = candidate.table_number
                task.task_status = "WAITING_FOR_DISH"
                await db.flush()
            return
        except IntegrityError:
            await db.refresh(task)
            continue


async def _get_or_create_task(
    db: AsyncSession, robot_id: str, task_id: int, dish_id: int | None = None
) -> RobotTask:
    task = (
        await db.execute(
            select(RobotTask).where(
                RobotTask.robot_id == robot_id, RobotTask.task_id == task_id
            )
        )
    ).scalar_one_or_none()
    if task is None:
        task = RobotTask(robot_id=robot_id, task_id=task_id, dish_id=dish_id)
        db.add(task)
        await db.flush()
    return task


async def receive_detections(db: AsyncSession, robot_id: str, data: dict) -> dict:
    body = DetectionPayload.model_validate(data)
    if not await _dish_exists(db, body.dish_id):
        raise ValueError("Không tìm thấy món")

    db.add(
        RobotDetection(
            detection_id=str(uuid.uuid4()),
            robot_id=robot_id,
            task_id=body.task_id,
            dish_id=body.dish_id,
        )
    )
    task = await _get_or_create_task(db, robot_id, body.task_id, body.dish_id)
    if task.dish_id != body.dish_id and task.task_status == "WAITING_FOR_DISH":
        task.dish_id = body.dish_id
        task.detail_id = None
        task.order_id = None
        task.table_number = None
    if task.detail_id is None:
        task.dish_id = body.dish_id
        await _assign(db, task)
    await db.commit()
    return {
        "ok": True,
        **delivery_destination(
            (task.table_number, task.order_id) if task.detail_id is not None else None
        ),
    }


async def get_current_task(db: AsyncSession, robot_id: str, data: dict) -> dict:
    body = CurrentTaskPayload.model_validate(data)
    task = (
        await db.execute(
            select(RobotTask).where(
                RobotTask.robot_id == robot_id, RobotTask.task_id == body.task_id
            )
        )
    ).scalar_one_or_none()
    if task is not None and task.detail_id is not None and task.task_status != "FAILED":
        return delivery_destination((task.table_number, task.order_id))

    dish_id = body.dish_id
    if dish_id is None:
        detection = (
            await db.execute(
                select(RobotDetection.dish_id)
                .where(
                    RobotDetection.robot_id == robot_id,
                    RobotDetection.task_id == body.task_id,
                )
                .order_by(RobotDetection.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        dish_id = detection
    if dish_id is None:
        return delivery_destination(None)
    if not await _dish_exists(db, dish_id):
        raise ValueError("Không tìm thấy món")
    task = task or await _get_or_create_task(db, robot_id, body.task_id, dish_id)
    if task.detail_id is None:
        task.dish_id = dish_id
        await _assign(db, task)
        await db.commit()
    return delivery_destination((task.table_number, task.order_id) if task.detail_id else None)


async def upload_best_image(db: AsyncSession, robot_id: str, data: dict) -> dict:
    body = BestImagePayload.model_validate(data)
    if not body.content_type.startswith("image/"):
        raise ValueError("Chỉ chấp nhận file ảnh")
    try:
        raw = await asyncio.to_thread(base64.b64decode, body.image_base64, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("image_base64 không hợp lệ") from exc
    if not raw:
        raise ValueError("Ảnh rỗng")
    if len(raw) > settings.ROBOT_MAX_IMAGE_BYTES:
        raise ValueError(f"Ảnh vượt quá {settings.ROBOT_MAX_IMAGE_BYTES // (1024 * 1024)} MB")

    task = (
        await db.execute(
            select(RobotTask).where(
                RobotTask.robot_id == robot_id, RobotTask.task_id == body.task_id
            )
        )
    ).scalar_one_or_none()
    dish_id = body.dish_id if body.dish_id is not None else (task.dish_id if task else None)
    if dish_id is not None and not await _dish_exists(db, dish_id):
        raise ValueError("Không tìm thấy món")

    image_id = f"IMAGE_{uuid.uuid4().hex[:12].upper()}"
    stmt = mysql_insert(RobotBestImage).values(
        image_id=image_id,
        robot_id=robot_id,
        task_id=body.task_id,
        dish_id=dish_id,
        mime_type=body.content_type,
        image_data=raw,
        updated_at=func.now(),
    )
    await db.execute(
        stmt.on_duplicate_key_update(
            image_id=stmt.inserted.image_id,
            dish_id=stmt.inserted.dish_id,
            mime_type=stmt.inserted.mime_type,
            image_data=stmt.inserted.image_data,
            updated_at=func.now(),
        )
    )
    await db.commit()
    return {"ok": True, "saved": True, "image_id": image_id}


async def receive_event(db: AsyncSession, robot_id: str, data: dict) -> dict:
    body = EventPayload.model_validate(data)
    db.add(
        RobotEvent(
            event_id=str(uuid.uuid4()),
            robot_id=robot_id,
            event_type=body.event_type,
            severity=body.severity,
            message=body.message,
        )
    )
    await db.commit()
    return {"ok": True}


async def receive_status(db: AsyncSession, robot_id: str, data: dict) -> dict:
    body = StatusPayload.model_validate(data)
    if body.order_id is not None:
        order_exists = await db.execute(select(exists().where(Order.order_id == body.order_id)))
        if not order_exists.scalar():
            raise ValueError("Không tìm thấy đơn hàng")

    stmt = mysql_insert(RobotDeliveryState).values(
        robot_id=robot_id,
        delivery_status=body.delivery_status,
        table_number=body.table_number,
        order_id=body.order_id,
        obstacle_detected=body.obstacle_detected,
        updated_at=func.now(),
    )
    await db.execute(
        stmt.on_duplicate_key_update(
            delivery_status=stmt.inserted.delivery_status,
            table_number=stmt.inserted.table_number,
            order_id=stmt.inserted.order_id,
            obstacle_detected=stmt.inserted.obstacle_detected,
            updated_at=func.now(),
        )
    )

    if body.order_id is not None and body.delivery_status in {"DELIVERING", "DELIVERED"}:
        task_statuses = ("WAITING_FOR_DISH",) if body.delivery_status == "DELIVERING" else (
            "WAITING_FOR_DISH", "DELIVERING"
        )
        tasks = (
            await db.execute(
                select(RobotTask).where(
                    RobotTask.robot_id == robot_id,
                    RobotTask.order_id == body.order_id,
                    RobotTask.task_status.in_(task_statuses),
                )
            )
        ).scalars().all()
        for task in tasks:
            task.task_status = body.delivery_status
            if body.delivery_status == "DELIVERED" and task.detail_id is not None:
                await db.execute(
                    update(OrderDetail)
                    .where(OrderDetail.detail_id == task.detail_id)
                    .values(served_status=True)
                )
        if body.delivery_status == "DELIVERED":
            order = (
                await db.execute(select(Order).where(Order.order_id == body.order_id))
            ).scalar_one()
            unserved = await db.execute(
                select(exists().where(
                    OrderDetail.order_id == body.order_id,
                    OrderDetail.served_status.is_not(True),
                ))
            )
            if not unserved.scalar() and order.order_status in ("PROCESSING", "PREPARING"):
                order.order_status = "DELIVERING"

    await db.commit()
    return {"ok": True, "robot_id": robot_id, "status": body.delivery_status}


async def get_pending_commands(db: AsyncSession, robot_id: str) -> list[dict]:
    rows = (
        await db.execute(
            select(RobotCommand)
            .where(
                RobotCommand.robot_id == robot_id,
                RobotCommand.command_status == "PENDING",
            )
            .order_by(RobotCommand.created_at.asc())
            .limit(20)
        )
    ).scalars().all()
    commands = []
    for row in rows:
        try:
            payload = json.loads(row.payload_json or "{}")
        except (TypeError, json.JSONDecodeError):
            payload = {}
        commands.append(
            {"command_id": row.command_id, "command": row.command, "payload": payload}
        )
    return commands


async def acknowledge_command(db: AsyncSession, robot_id: str, data: dict) -> dict:
    body = AckPayload.model_validate(data)
    command = (
        await db.execute(
            select(RobotCommand).where(
                RobotCommand.command_id == body.command_id,
                RobotCommand.robot_id == robot_id,
            )
        )
    ).scalar_one_or_none()
    if command is None:
        raise ValueError("Không tìm thấy lệnh")
    command.command_status = body.status
    command.completed_at = datetime.now()
    if command.command == "RESET_STATUS" and body.status == "DONE":
        state = mysql_insert(RobotDeliveryState).values(
            robot_id=robot_id,
            delivery_status="NOT_DELIVERED",
            table_number=None,
            order_id=None,
            obstacle_detected=False,
            updated_at=func.now(),
        )
        await db.execute(
            state.on_duplicate_key_update(
                delivery_status="NOT_DELIVERED",
                table_number=None,
                order_id=None,
                obstacle_detected=False,
                updated_at=func.now(),
            )
        )
        await db.execute(
            update(RobotTask)
            .where(
                RobotTask.robot_id == robot_id,
                RobotTask.task_status.in_(("WAITING_FOR_DISH", "DELIVERING")),
            )
            .values(task_status="FAILED", detail_id=None, order_id=None, table_number=None)
        )
    await db.commit()
    return {"ok": True}


async def create_command(
    db: AsyncSession, robot_id: str, command: str, payload: dict
) -> RobotCommand:
    command_row = RobotCommand(
        command_id=str(uuid.uuid4()),
        robot_id=robot_id,
        command=command,
        payload_json=_dumps(payload),
        command_status="PENDING",
    )
    db.add(command_row)
    await db.commit()
    return command_row


async def dispatch_action(db: AsyncSession, robot_id: str, action: str, data: dict) -> dict:
    handlers = {
        "send_detections": receive_detections,
        "get_current_task": get_current_task,
        "upload_best_image": upload_best_image,
        "send_event": receive_event,
        "send_status": receive_status,
        "get_commands": lambda session, device, payload: get_pending_commands(session, device),
        "acknowledge_command": acknowledge_command,
    }
    handler = handlers.get(action)
    if handler is None:
        raise ValueError(f"Action không được hỗ trợ: {action}")
    result = await handler(db, robot_id, data)
    return {"commands": result} if action == "get_commands" else result
