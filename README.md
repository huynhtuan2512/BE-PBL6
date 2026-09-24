# Robot Phục Vụ Nhà Hàng - Backend API

Backend FastAPI (async) + MySQL cho hệ thống Robot tự hành điều hướng bằng mã QR,
tích hợp ESP32-CAM, Raspberry Pi (AI) và ThingsBoard IoT Platform.

## Cài đặt

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # rồi chỉnh sửa thông tin DATABASE_URL, SECRET_KEY...
```

## Khởi tạo database & migration

```bash
alembic revision --autogenerate -m "init 10 tables"
alembic upgrade head
```

## Chạy server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Swagger UI: http://localhost:8000/docs

## Ghi chú xác thực

| Đối tượng            | Cơ chế                          |
|-----------------------|----------------------------------|
| ADMIN / STAFF          | OAuth2 Bearer JWT (`/auth/login`) |
| ESP32_ROBOT / RASPBERRY_PI | Header tĩnh `X-Device-Key: <DEVICE_API_KEY>` |

## Luồng định tuyến Robot (tóm tắt)

1. Robot quét QR tại node hiện tại → gọi `GET /api/v1/robot/routing`.
2. Backend tra bảng `routings` (ma trận tiền tính toán) → trả về danh sách bước đi.
3. Khi giao món xong, robot gọi lại API với `direction=INBOUND` → Backend **đảo ngược**
   path_steps của lượt đi tương ứng để tạo đường về, không cần lưu thêm dữ liệu route riêng.
