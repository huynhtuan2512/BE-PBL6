"""
app/api/v1/endpoints/hardware.py
----------------------------------
Router dành riêng cho thiết bị IoT: ESP32-CAM (robot) và Raspberry Pi (AI).
Toàn bộ endpoint trong file này xác thực bằng Header `X-Device-Key`
(KHÔNG dùng JWT vì đây là máy-với-máy, không phải người dùng đăng nhập).
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppException
from app.core.security import require_roles, verify_device_key
from app.models.dish import Dish
from app.models.order import Order, OrderDetail
from app.models.robot import RobotStatus
from app.schemas.common import SuccessResponse
from app.schemas.hardware import (
    AIDetectDishRequest,
    AIDetectHumanRequest,
    RobotRoutingResponse,
    RobotStatusResponse,
    RobotStatusUpdate,
)
from app.services.routing_service import RoutingService

router = APIRouter(prefix="/robot", tags=["Hardware - ESP32 & Raspberry Pi"])
hardware_router = APIRouter(prefix="/hardware", tags=["Hardware - ESP32 & Raspberry Pi"])


# ============================================================================
# 1. ROUTING: ESP32 quét QR -> hỏi Backend "bước tiếp theo là gì?"
# ============================================================================
@router.get(
    "/routing",
    response_model=SuccessResponse[RobotRoutingResponse],
    summary="ESP32 gửi mã QR vừa quét được để nhận chỉ dẫn bước đi tiếp theo",
)
async def get_robot_routing(
    robot_id: str = Query(..., description="Mã robot, VD: ROBOT_01"),
    current_qr_id: str = Query(..., description="Mã QR robot vừa quét được tại node hiện tại"),
    target_table_number: int | None = Query(
        default=None, description="Bàn đích (bắt buộc khi direction=OUTBOUND)"
    ),
    direction: str = Query(default="OUTBOUND", description="OUTBOUND (đi giao món) | INBOUND (quay về bếp)"),
    db: AsyncSession = Depends(get_db),
    _device: str = Depends(verify_device_key),  # xác thực bằng X-Device-Key, không cần dùng giá trị trả về
):
    """
    Luồng hoạt động thực tế trên Robot:
    1. Robot quét QR tại node hiện tại -> đọc được `current_node_code`.
    2. Robot gọi API này (GET, để nhẹ cho ESP32, không cần gửi body).
    3. Backend tra bảng `routings` (ma trận đường đi tiền tính toán) để trả về
       danh sách bước đi tiếp theo cho tới khi tới đích.
    4. Robot thực hiện lần lượt từng "action" (STRAIGHT/LEFT/RIGHT) cho tới node kế tiếp,
       rồi lặp lại bước 1 khi quét được QR mới.
    """
    service = RoutingService(db)
    result = await service.resolve_routing(
        robot_id=robot_id,
        current_qr_id=current_qr_id,
        target_table_number=target_table_number,
        direction=direction,
    )
    return SuccessResponse(data=result, message="Lấy chỉ dẫn định tuyến thành công")


# ============================================================================
# 2. ROBOT STATUS HEARTBEAT: ESP32 định kỳ báo cáo trạng thái/pin
# ============================================================================
@router.post(
    "/status",
    response_model=SuccessResponse[RobotStatusResponse],
    summary="ESP32 gửi heartbeat cập nhật trạng thái & pin định kỳ (VD mỗi 5s)",
)
async def update_robot_status(
    payload: RobotStatusUpdate,
    db: AsyncSession = Depends(get_db),
    _device: str = Depends(verify_device_key),
):
    result = await db.execute(select(RobotStatus).where(RobotStatus.id == payload.id))
    robot = result.scalar_one_or_none()

    if robot is None:
        robot = RobotStatus(
            id=payload.id,
            robot_state=payload.robot_state,
            current_qr_id=payload.current_qr_id,
            obstacle_detected=payload.obstacle_detected,
        )
        db.add(robot)
    else:
        robot.robot_state = payload.robot_state
        robot.current_qr_id = payload.current_qr_id
        robot.obstacle_detected = payload.obstacle_detected

    await db.commit()
    await db.refresh(robot)
    return SuccessResponse(data=robot, message="Cập nhật trạng thái robot thành công")


@router.get("/status", response_model=SuccessResponse[list[RobotStatusResponse]])
async def list_robot_status(
    db: AsyncSession = Depends(get_db),
    _staff=Depends(require_roles("ADMIN", "STAFF")),
):
    robots = (await db.execute(select(RobotStatus).order_by(RobotStatus.id))).scalars().all()
    return SuccessResponse(data=[RobotStatusResponse.model_validate(robot) for robot in robots])


# ============================================================================
# 3. AI DETECT DISHES: Raspberry Pi xác nhận món ăn đúng với đơn hàng trước khi robot rời bếp
# ============================================================================
@hardware_router.put(
    "/ai/detect-dishes",
    response_model=SuccessResponse[dict],
    summary="Raspberry Pi gửi kết quả AI nhận diện món ăn trên khay để đối chiếu với đơn hàng",
)
async def ai_detect_dishes(
    payload: AIDetectDishRequest,
    db: AsyncSession = Depends(get_db),
    _device: str = Depends(verify_device_key),
):
    order = (await db.execute(select(Order).where(Order.order_id == payload.order_id))).scalar_one_or_none()
    if order is None:
        raise AppException(404, "Không tìm thấy đơn hàng")
    expected = (await db.execute(
        select(Dish.ai_label_id).join(OrderDetail, OrderDetail.dish_id == Dish.dish_id).where(
            OrderDetail.order_id == payload.order_id, Dish.ai_label_id.isnot(None)
        )
    )).scalars().all()
    expected_labels = set(expected)
    detected_labels = set(payload.detected_labels)
    unmatched = sorted(expected_labels - detected_labels)
    unexpected = sorted(detected_labels - expected_labels)
    is_matched = not unmatched and not unexpected

    if not is_matched:
        # Không raise lỗi cứng: vẫn trả về kết quả để robot/nhân viên tự quyết định xử lý tiếp
        return SuccessResponse(
            data={"is_matched": False, "unmatched_labels": unmatched, "unexpected_labels": unexpected},
            message="Phát hiện món ăn KHÔNG khớp với đơn hàng, vui lòng kiểm tra lại khay đồ ăn",
        )

    return SuccessResponse(
        data={"is_matched": True, "unmatched_labels": [], "unexpected_labels": []},
        message="Món ăn khớp với đơn hàng",
    )


# ============================================================================
# 4. AI DETECT HUMAN: Raspberry Pi phát hiện người cản đường -> robot tạm dừng
# ============================================================================
@router.post(
    "/ai/detect-human",
    response_model=SuccessResponse[dict],
    summary="Raspberry Pi gửi kết quả AI phát hiện người cản đường để robot quyết định dừng/né",
)
async def ai_detect_human(
    payload: AIDetectHumanRequest,
    _device: str = Depends(verify_device_key),
):
    # Ngưỡng tin cậy tối thiểu để coi là phát hiện thật (tránh false positive làm robot dừng oan)
    CONFIDENCE_THRESHOLD = 0.6

    should_stop = payload.person_detected and payload.confidence >= CONFIDENCE_THRESHOLD

    return SuccessResponse(
        data={
            "should_stop": should_stop,
            "robot_id": payload.robot_id,
            "qr_id": payload.qr_id,
        },
        message="Đã xử lý cảnh báo vật cản/người đi đường",
    )
