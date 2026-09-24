"""
app/services/thingsboard_service.py
-------------------------------------
Giao tiếp với ThingsBoard IoT Platform:
- REST API: lấy JWT token của ThingsBoard, gửi RPC command xuống robot (VD: lệnh dừng khẩn cấp).
- Dữ liệu telemetry (battery, vị trí...) do ESP32/Raspberry Pi tự đẩy trực tiếp lên ThingsBoard
  qua MQTT (không qua Backend này), Backend chỉ cần gọi REST API của ThingsBoard khi cần
  ĐIỀU KHIỂN NGƯỢC xuống thiết bị (Server-Side RPC).
"""

import httpx

from app.core.config import settings


class ThingsBoardService:
    """Client mỏng để gọi REST API của ThingsBoard."""

    def __init__(self):
        self.base_url = settings.THINGSBOARD_REST_URL.rstrip("/")
        self._jwt_token: str | None = None

    async def _login(self) -> str:
        """Đăng nhập lấy JWT token của ThingsBoard (khác hoàn toàn JWT nội bộ của app)."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/auth/login",
                json={
                    "username": settings.THINGSBOARD_USERNAME,
                    "password": settings.THINGSBOARD_PASSWORD,
                },
                timeout=10,
            )
            resp.raise_for_status()
            self._jwt_token = resp.json()["token"]
            return self._jwt_token

    async def send_rpc_command(self, device_id: str, method: str, params: dict) -> dict:
        """
        Gửi lệnh điều khiển từ Backend xuống thiết bị thông qua ThingsBoard Server-Side RPC.
        Ví dụ: method="emergencyStop", params={} để dừng khẩn cấp robot từ xa qua Dashboard Admin.
        """
        if self._jwt_token is None:
            await self._login()

        headers = {"X-Authorization": f"Bearer {self._jwt_token}"}
        payload = {"method": method, "params": params, "timeout": 5000}

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/rpc/oneway/{device_id}",
                json=payload,
                headers=headers,
                timeout=10,
            )
            # Nếu token hết hạn, đăng nhập lại 1 lần rồi thử lại
            if resp.status_code == 401:
                await self._login()
                headers = {"X-Authorization": f"Bearer {self._jwt_token}"}
                resp = await client.post(
                    f"{self.base_url}/api/rpc/oneway/{device_id}", json=payload, headers=headers, timeout=10
                )

            resp.raise_for_status()
            return {"status": "sent", "method": method}


# Instance dùng chung (stateless-ish, chỉ cache JWT token của ThingsBoard)
thingsboard_service = ThingsBoardService()
