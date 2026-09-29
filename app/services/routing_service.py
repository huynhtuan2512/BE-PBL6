"""QR routing service backed by the ``routings`` SQL dump table."""

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.models.node import Node
from app.models.robot import RobotStatus, RobotTravelLog
from app.models.routing import Routing
from app.models.table import Table
from app.schemas.hardware import RobotRoutingResponse, RouteStep

DIRECTION_OUTBOUND = "OUTBOUND"
DIRECTION_INBOUND = "INBOUND"


class RoutingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_node_by_qr(self, qr_id: str) -> Node:
        node = (
            await self.db.execute(select(Node).where(Node.qr_id == qr_id))
        ).scalar_one_or_none()
        if node is None:
            raise AppException(status_code=404, message=f"Không tìm thấy node với mã QR: {qr_id}")
        return node

    async def _get_kitchen_node(self) -> Node:
        node = (
            await self.db.execute(
                select(Node).where(Node.node_type.in_(["START", "KITCHEN"]))
            )
        ).scalars().first()
        if node is None:
            raise AppException(status_code=500, message="Chưa cấu hình node bếp")
        return node

    async def _get_table_node(self, table_number: int) -> Node:
        table = (
            await self.db.execute(select(Table).where(Table.table_number == table_number))
        ).scalar_one_or_none()
        if table is None:
            raise AppException(status_code=404, message=f"Không tìm thấy bàn số: {table_number}")
        return await self._get_node_by_qr(table.qr_id)

    async def _lookup_routing(self, qr_id: str, target_qr_id: str) -> Routing | None:
        result = await self.db.execute(
            select(Routing)
            .where(
                Routing.qr_id == qr_id,
                (Routing.target_table_id == target_qr_id) | (Routing.target_table_id.is_(None)),
            )
            .order_by(Routing.target_table_id.is_(None))
        )
        return result.scalars().first()

    async def resolve_routing(
        self,
        robot_id: str,
        current_qr_id: str,
        target_table_number: int | None,
        direction: str,
    ) -> RobotRoutingResponse:
        current_node = await self._get_node_by_qr(current_qr_id)
        if direction == DIRECTION_OUTBOUND:
            if target_table_number is None:
                raise AppException(status_code=400, message="Thiếu target_table_number cho lượt đi")
            target_node = await self._get_table_node(target_table_number)
            to_node = target_node
        elif direction == DIRECTION_INBOUND:
            to_node = await self._get_kitchen_node()
        else:
            raise AppException(status_code=400, message="direction phải là OUTBOUND hoặc INBOUND")

        if current_node.qr_id == to_node.qr_id:
            steps = [RouteStep(qr_id=current_node.qr_id, action="STOP")]
        else:
            route = await self._lookup_routing(current_node.qr_id, to_node.qr_id)
            if route is None:
                raise AppException(status_code=404, message="Không tìm thấy đường đi phù hợp")
            steps = [RouteStep(qr_id=current_node.qr_id, action=route.action)]

        await self._create_travel_log(robot_id, steps)
        return RobotRoutingResponse(
            robot_id=robot_id,
            direction=direction,
            from_qr_id=current_node.qr_id,
            to_qr_id=to_node.qr_id,
            total_steps=len(steps),
            steps=steps,
            is_final_node=len(steps) == 1 and steps[0].action == "STOP",
        )

    async def _create_travel_log(self, robot_id: str, steps: list[RouteStep]) -> None:
        robot = (
            await self.db.execute(select(RobotStatus).where(RobotStatus.id == robot_id))
        ).scalar_one_or_none()
        if robot is None or robot.current_order_id is None:
            return

        for index, step in enumerate(steps, start=1):
            self.db.add(
                RobotTravelLog(
                    log_id=f"LOG_{uuid4().hex[:12].upper()}",
                    order_id=robot.current_order_id,
                    qr_id=step.qr_id,
                    action_taken=step.action,
                    step_order=index,
                )
            )
        await self.db.commit()
