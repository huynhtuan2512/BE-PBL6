
- Raspberry Pi xác thực bằng header `X-Device-Key`.

## Base URL

```text
http://<SERVER_HOST>:<PORT>/api/v1/robots/<robot_id>
```


## Header chung

Mọi request của Raspberry Pi đều phải gửi:

```http
X-Device-Key: <DEVICE_API_KEY>
Content-Type: application/json
```
Server dùng cơ chế so sánh khóa hiện tại :

```text
is_valid_device_key()
```



## Response chuẩn


```json
{
  "status": "success",
  "data": {},
  "message": null
}
```


Response lỗi HTTP:

```json
{
  "status": "error",
  "message": "Nội dung lỗi"
}
```

lỗi validation của FastAPI:

```json
{
  "detail": "Nội dung lỗi"
}
```

## 1. Gửi món nhận diện



```http
POST /api/v1/robots/{robot_id}/detections
```

Ví dụ:

```http
POST /api/v1/robots/R01/detections
X-Device-Key: <DEVICE_API_KEY>
Content-Type: application/json
```

Request body:

```json
{
  "task_id": 1,
  "dish_id": 7
}
```


Response khi tìm thấy đơn:

```json
{
  "status": "success",
  "data": {
    "ok": true,
    "has_task": true,
    "table_number": 5,
    "order_id": "ORDER_001"
  }
}
```

Response khi chưa tìm thấy đơn:

```json
{
  "status": "success",
  "data": {
    "ok": true,
    "has_task": false,
    "table_number": null,
    "order_id": null
  }
}
```

Tình huống lỗi:

- `401`: sai hoặc thiếu `X-Device-Key`.
- `404`: không tìm thấy món.
- `422`: `task_id` hoặc `dish_id` không hợp lệ.
- `500`: lỗi xử lý database.

## 2. Hỏi task giao hàng hiện tại


```http
POST /api/v1/robots/{robot_id}/tasks/current
```

Request khi đã biết món:

```json
{
  "task_id": 1,
  "dish_id": 7
}
```

Request khi muốn server dùng detection gần nhất:

```json
{
  "task_id": 1
}
```

Schema:

- `task_id`: integer, lớn hơn hoặc bằng `0`.
- `dish_id`: integer, tùy chọn, lớn hơn hoặc bằng `0`.

Có nhiệm vụ:

```json
{
  "status": "success",
  "data": {
    "has_task": true,
    "table_number": 5,
    "order_id": "ORDER_001"
  }
}
```

Không có nhiệm vụ:

```json
{
  "status": "success",
  "data": {
    "has_task": false,
    "table_number": null,
    "order_id": null
  }
}
```

## 3. Gửi ảnh tốt nhất


```http
POST /api/v1/robots/{robot_id}/images/best
```

Request body:

```json
{
  "task_id": 1,
  "content_type": "image/jpeg",
  "image_base64": "...",
  "dish_id": 7
}
```


Response thành công:

```json
{
  "status": "success",
  "data": {
    "ok": true,
    "saved": true,
    "image_id": "IMAGE_001"
  }
}
```

Server ghi đè ảnh hiện tại của cùng `robot_id` và `task_id`.


## 4. Gửi sự kiện hoặc log

```http
POST /api/v1/robots/{robot_id}/events
```

Request body:

```json
{
  "event_type": "OBSTACLE_DETECTED",
  "message": "Obstacle",
  "severity": "WARNING"
}
```

Schema:

- `event_type`: chuỗi `1-50` ký tự.
- `message`: chuỗi `1-2000` ký tự.
- `severity`: `INFO`, `WARNING` hoặc `ERROR`.
- `severity` mặc định là `INFO`.

Response:

```json
{
  "status": "success",
  "data": {
    "ok": true
  }
}
```

## 5. Gửi trạng thái robot

```http
POST /api/v1/robots/{robot_id}/status
```

Request body:

```json
{
  "delivery_status": "DELIVERING",
  "table_number": 5,
  "order_id": "ORDER_001",
  "obstacle_detected": false
}
```
Response:

```json
{
  "status": "success",
  "data": {
    "ok": true,
    "robot_id": "R01",
    "status": "DELIVERING"
  }
}
```

## 6. Lấy command đang chờ

Chu kỳ đề xuất:

```text
2-5 giây
```

```http
GET /api/v1/robots/{robot_id}/commands
```

Response:

```json
{
  "status": "success",
  "data": {
    "commands": [
      {
        "command_id": "C1",
        "command": "STOP",
        "payload": {}
      }
    ]
  }
}
```

Command hợp lệ:

- `STOP`
- `RETURN_TO_KITCHEN`
- `RESET_STATUS`

Server có thể trả tối đa `20` command PENDING trên mỗi lần gọi.

## 7. Xác nhận command


```http
POST /api/v1/robots/{robot_id}/commands/{command_id}/acknowledge
```

Ví dụ:

```http
POST /api/v1/robots/R01/commands/C1/acknowledge
X-Device-Key: <DEVICE_API_KEY>
Content-Type: application/json
```

Payload khi xử lý thành công:

```json
{
  "status": "DONE"
}
```

Payload khi xử lý thất bại:

```json
{
  "status": "FAILED"
}
```

Schema:

- `status`: bắt buộc, chỉ nhận `DONE` hoặc `FAILED`.

Response thành công:

```json
{
  "status": "success",
  "data": {
    "ok": true
  }
}
```

Trường hợp không tìm thấy command thuộc robot hiện tại:

```json
{
  "status": "error",
  "message": "Không tìm thấy lệnh"
}
```

HTTP status:

- `404 Not Found`.

## 8. Danh sách endpoint

| Chức năng | Method | Endpoint |
|---|---|---|
| Gửi món nhận diện | `POST` | `/api/v1/robots/{robot_id}/detections` |
| Hỏi task hiện tại | `POST` | `/api/v1/robots/{robot_id}/tasks/current` |
| Gửi ảnh tốt nhất | `POST` | `/api/v1/robots/{robot_id}/images/best` |
| Gửi event/log | `POST` | `/api/v1/robots/{robot_id}/events` |
| Gửi trạng thái | `POST` | `/api/v1/robots/{robot_id}/status` |
| Lấy command chờ | `GET` | `/api/v1/robots/{robot_id}/commands` |
| Xác nhận command | `POST` | `/api/v1/robots/{robot_id}/commands/{command_id}/acknowledge` |

## 9. Luồng hoạt động HTTP

Luồng tiêu biểu:

```text
Raspberry nhận diện món
  ↓
POST /detections
  ↓
Server trả table_number và order_id
  ↓
Raspberry điều hướng tới bàn
  ↓
POST /status
  ↓
GET /commands mỗi 2-5 giây
  ↓
Raspberry nhận và xử lý command
  ↓
POST /commands/{command_id}/acknowledge
```


## 12. API quản trị hiện có

Các API REST quản trị robot hiện tại vẫn có thể dùng riêng cho người quản trị:

```http
GET /api/v1/admin/robots
POST /api/v1/admin/robots/{robot_id}/commands
GET /api/v1/admin/robots/{robot_id}/commands
GET /api/v1/admin/robots/{robot_id}/images/{task_id}
```

Các API này yêu cầu JWT và role `ADMIN` hoặc `STAFF`, không dùng `X-Device-Key`.
