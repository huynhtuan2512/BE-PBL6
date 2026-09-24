"""
app/services/routing_service.py
--------------------------------
Business logic cốt lõi cho việc điều hướng Robot bằng QR Code.

Ý tưởng tổng quát:
- Sơ đồ nhà hàng được mô hình hóa thành đồ thị các `Node` (đỉnh) nối với nhau.
- Bảng `routings` lưu sẵn (precompute) đường đi tối ưu giữa mọi cặp (from_node, to_node)
  dưới dạng danh sách bước (path_steps), để lúc runtime chỉ cần TRA MA TRẬN (tra bảng)
  thay vì chạy lại thuật toán tìm đường mỗi lần ESP32 gọi API -> tối ưu tốc độ phản hồi.
- Khi Robot đã giao món xong tại bàn (lượt đi - OUTBOUND), nó cần quay về bếp
  (lượt về - INBOUND). Thay vì phải lưu thêm 1 bản ghi routing riêng cho chiều ngược lại,
  ta ĐẢO NGƯỢC (reverse) chính path_steps của lượt đi, đồng thời đảo ngược hành động
  rẽ trái/phải cho đúng với hướng di chuyển ngược chiều.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.models.node import Node
from app.models.robot import RobotTravelLog, TravelLogStatus
from app.models.routing import Routing
from app.models.table import Table
from app.schemas.hardware import RobotRoutingResponse, RouteStep

# Bảng tra đảo ngược hành động: khi đi ngược chiều, rẽ trái lúc đi -> phải là rẽ phải lúc về
ACTION_REVERSE_MAP = {
    "LEFT": "RIGHT",
    "RIGHT": "LEFT",
    "STRAIGHT": "STRAIGHT",
    "STOP": "STOP",
}

DIRECTION_OUTBOUND = "OUTBOUND"  # lượt đi: bếp -> bàn
DIRECTION_INBOUND = "INBOUND"    # lượt về: bàn -> bếp


class RoutingService:
    """Service xử lý toàn bộ nghiệp vụ định tuyến cho Robot."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Helper: tìm Node theo node_code (mã QR)
    # ------------------------------------------------------------------
    async def _get_node_by_code(self, node_code: str) -> Node:
        result = await self.db.execute(select(Node).where(Node.node_code == node_code))
        node = result.scalar_one_or_none()
        if node is None:
            raise AppException(status_code=404, message=f"Không tìm thấy node với mã QR: {node_code}")
        return node

    async def _get_kitchen_node(self) -> Node:
        """Node bếp - điểm xuất phát mặc định của mọi robot (giả định chỉ có 1 bếp)."""
        result = await self.db.execute(select(Node).where(Node.node_type == "KITCHEN"))
        node = result.scalars().first()
        if node is None:
            raise AppException(status_code=500, message="Chưa cấu hình node BẾP (KITCHEN) trong hệ thống")
        return node

    async def _get_table_node(self, table_number: str) -> Node:
        result = await self.db.execute(
            select(Table).where(Table.table_number == table_number)
        )
        table = result.scalar_one_or_none()
        if table is None:
            raise AppException(status_code=404, message=f"Không tìm thấy bàn số: {table_number}")

        node_result = await self.db.execute(select(Node).where(Node.id == table.node_id))
        node = node_result.scalar_one_or_none()
        if node is None:
            raise AppException(status_code=500, message="Bàn chưa được gắn với node nào trên sơ đồ")
        return node

    # ------------------------------------------------------------------
    # Tra ma trận routing (bảng routings) giữa 2 node cho trước
    # ------------------------------------------------------------------
    async def _lookup_routing(self, from_node_id: int, to_node_id: int) -> Routing:
        result = await self.db.execute(
            select(Routing).where(
                Routing.from_node_id == from_node_id,
                Routing.to_node_id == to_node_id,
                Routing.is_active == True,  # noqa: E712
            )
        )
        routing = result.scalar_one_or_none()
        if routing is None:
            raise AppException(
                status_code=404,
                message="Không tìm thấy đường đi phù hợp trong ma trận routing giữa 2 node",
            )
        return routing

    @staticmethod
    def _reverse_path(path_steps: list[dict]) -> list[dict]:
        """
        Đảo ngược 1 chuỗi bước đi (path_steps) để dùng cho chiều di chuyển ngược lại.

        Nguyên lý:
        1) Đảo ngược THỨ TỰ danh sách node (đi từ cuối về đầu).
        2) Với mỗi bước, hành động (action) áp dụng TẠI node đó phải "dịch pha" 1 bước
           so với thứ tự cũ, vì action ở bước i (lượt đi) mô tả việc rẽ SAU KHI đi qua
           node i để tới node i+1; khi đảo chiều, hành động đó phải gắn vào node i+1
           và được đảo trái<->phải.
        """
        if not path_steps:
            return []

        reversed_nodes = list(reversed([step["node_code"] for step in path_steps]))
        # Hành động gốc theo thứ tự cũ (bỏ node đầu vì node đầu không có action "tới")
        original_actions = [step["action"] for step in path_steps]

        new_steps: list[dict] = []
        for idx, node_code in enumerate(reversed_nodes):
            if idx == len(reversed_nodes) - 1:
                # Node cuối cùng của lượt về = điểm xuất phát của lượt đi => luôn STOP
                new_steps.append({"node_code": node_code, "action": "STOP"})
            else:
                # Lấy action tương ứng theo thứ tự cũ (đảo ngược index) rồi đảo trái/phải
                original_action = original_actions[len(original_actions) - 1 - idx] if idx < len(original_actions) else "STRAIGHT"
                new_steps.append(
                    {"node_code": node_code, "action": ACTION_REVERSE_MAP.get(original_action, "STRAIGHT")}
                )

        return new_steps

    # ------------------------------------------------------------------
    # API chính: xử lý request routing từ ESP32 khi quét QR
    # ------------------------------------------------------------------
    async def resolve_routing(
        self,
        robot_code: str,
        current_node_code: str,
        target_table_number: str | None,
        direction: str,
    ) -> RobotRoutingResponse:
        """
        Trả về chuỗi bước đi tiếp theo cho Robot dựa trên vị trí hiện tại (vừa quét QR)
        và hướng di chuyển (OUTBOUND: đi giao món | INBOUND: quay về bếp).
        """
        current_node = await self._get_node_by_code(current_node_code)

        if direction == DIRECTION_OUTBOUND:
            # ---- LƯỢT ĐI: từ vị trí hiện tại -> bàn đích ----
            if not target_table_number:
                raise AppException(status_code=400, message="Thiếu target_table_number cho lượt đi (OUTBOUND)")

            target_node = await self._get_table_node(target_table_number)
            routing = await self._lookup_routing(current_node.id, target_node.id)
            steps = routing.path_steps
            to_node_code = target_node.node_code

        elif direction == DIRECTION_INBOUND:
            # ---- LƯỢT VỀ: đảo ngược đường đi đã lưu lúc đi để quay lại bếp ----
            kitchen_node = await self._get_kitchen_node()

            # Tra lại routing gốc (bếp -> vị trí hiện tại) rồi đảo ngược, thay vì
            # lưu thêm 1 bản ghi routing riêng cho chiều về => tiết kiệm dữ liệu & đảm bảo nhất quán.
            original_routing = await self._lookup_routing(kitchen_node.id, current_node.id)
            steps = self._reverse_path(original_routing.path_steps)
            to_node_code = kitchen_node.node_code

        else:
            raise AppException(status_code=400, message="direction phải là OUTBOUND hoặc INBOUND")

        route_steps = [RouteStep(**step) for step in steps]
        is_final = len(route_steps) <= 1

        # Ghi log hành trình để truy vết / thống kê (robot_travel_logs)
        await self._create_travel_log(
            robot_code=robot_code,
            start_node_id=current_node.id,
            end_node_id=(await self._get_node_by_code(to_node_code)).id,
            direction=direction,
            path_taken=[s.model_dump() for s in route_steps],
        )

        return RobotRoutingResponse(
            robot_code=robot_code,
            direction=direction,
            from_node_code=current_node.node_code,
            to_node_code=to_node_code,
            total_steps=len(route_steps),
            steps=route_steps,
            is_final_node=is_final,
        )

    async def _create_travel_log(
        self,
        robot_code: str,
        start_node_id: int,
        end_node_id: int,
        direction: str,
        path_taken: list[dict],
    ) -> RobotTravelLog:
        log = RobotTravelLog(
            robot_code=robot_code,
            start_node_id=start_node_id,
            end_node_id=end_node_id,
            direction=direction,
            path_taken=path_taken,
            status=TravelLogStatus.IN_PROGRESS,
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log
