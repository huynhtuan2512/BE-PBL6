```text
ws://<SERVER_HOST>:<PORT>/ws/robot/<robot_id>
```

Kết nối phải gửi header:

```text
X-Device-Key: <DEVICE_API_KEY>
```

## Message tối giản

Raspberry gửi request:

```json
{
  "id": "1",
  "action": "send_detections",
  "payload": {}
}
```

Server trả response:

```json
{
  "id": "1",
  "ok": true,
  "data": {}
}
```

Response lỗi:

```json
{
  "id": "1",
  "ok": false,
  "error": "Nội dung lỗi"
}
```

1. Gửi món nhận diện được

Raspberry -> Server:

```json
{
  "id": "1",
  "action": "send_detections",
  "payload": {
    "task_id": 1,
    "dish_id": 7
  }
}
```

`task_id` phải là ID mới cho mỗi chuyến giao/thử giao. Sau khi task đã `DELIVERED` hoặc `FAILED`, gửi lại cùng `task_id` sẽ bị từ chối; dùng ID mới khi thử lại để tránh nhận task cũ. Mỗi phần ăn được lưu thành một dòng `OrderDetail` riêng với `quantity: 1`.

Server -> Raspberry khi tìm thấy đơn:

```json
{
  "id": "1",
  "ok": true,
  "data": {
    "ok": true,
    "has_task": true,
    "task_id": 1,
    "detail_id": "DTL_001",
    "table_number": 5
  }
}
```

Server -> Raspberry khi không tìm thấy đơn:

```json
{
  "id": "1",
  "ok": true,
  "data": {
    "ok": true,
    "has_task": false,
    "task_id": null,
    "detail_id": null,
    "table_number": null
  }
}
```

2. Hỏi nhiệm vụ giao hàng hiện tại

Nếu đã biết món:

```json
{
  "id": "2",
  "action": "get_current_task",
  "payload": {
    "task_id": 1,
    "dish_id": 7
  }
}
```

Nếu muốn server dùng detection gần nhất:

```json
{
  "id": "2",
  "action": "get_current_task",
  "payload": {
    "task_id": 1
  }
}
```

Có nhiệm vụ:

```json
{
  "id": "2",
  "ok": true,
  "data": {
    "has_task": true,
    "task_id": 1,
    "detail_id": "DTL_001",
    "table_number": 5
  }
}
```

Không có nhiệm vụ:

```json
{
  "id": "2",
  "ok": true,
  "data": {
    "has_task": false,
    "task_id": null,
    "detail_id": null,
    "table_number": null
  }
}
```

3. Gửi ảnh tốt nhất của task


Raspberry -> Server:

```json
{
  "id": "3",
  "action": "upload_best_image",
  "payload": {
    "task_id": 1,
    "content_type": "image/jpeg",
    "image_base64": "...",
    "dish_id": 7
  }
}
```
Lưu thành công (server luôn ghi đè ảnh hiện tại của cùng `robot_id` và `task_id`):

```json
{
  "id": "3",
  "ok": true,
  "data": {
    "ok": true,
    "saved": true,
    "image_id": "IMAGE_001"
  }
}
```

Server không nhận và không so sánh `confidence`; Raspberry tự chọn ảnh trước khi gửi.

4. Gửi sự kiện/log

```json
{
  "id": "4",
  "action": "send_event",
  "payload": {
    "event_type": "OBSTACLE_DETECTED",
    "message": "Obstacle",
    "severity": "WARNING"
  }
}
```

`severity` nhận `INFO`, `WARNING` hoặc `ERROR`.

Response:

```json
{
  "id": "4",
  "ok": true,
  "data": {
    "ok": true
  }
}
```

5. Gửi trạng thái robot


```json
{
  "id": "5",
  "action": "send_status",
  "payload": {
    "delivery_status": "DELIVERING",
    "detail_id": "DTL_001",
    "obstacle_detected": false
  }
}
```

Với `WAITING_FOR_DISH`, `DELIVERING` và `DELIVERED`, phải gửi `detail_id` do server trả về khi phân công task. Khi báo một món giao thất bại, gửi `NOT_DELIVERED` kèm `detail_id`; server giải phóng đúng task để món có thể được phân công lại. `NOT_DELIVERED` không có `detail_id` chỉ dùng để cập nhật trạng thái tổng thể/nhàn rỗi của robot. Không gửi `order_id` hoặc `table_number`; server tra cứu các giá trị này từ database.

`delivery_status` nhận một trong:

```text
NOT_DELIVERED
WAITING_FOR_DISH
DELIVERING
DELIVERED
```

Response:

```json
{
  "id": "5",
  "ok": true,
  "data": {
    "ok": true,
    "robot_id": "R01",
    "status": "DELIVERING",
    "detail_id": "DTL_001"
  }
}
```

6. Lấy và nhận command từ Server

Raspberry có thể hỏi command đang chờ:

```json
{
  "id": "6",
  "action": "get_commands",
  "payload": {}
}
```

Server trả:

```json
{
  "id": "6",
  "ok": true,
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

Server cũng có thể chủ động đẩy cùng command qua WebSocket:

```json
{
  "type": "command",
  "data": {
    "command_id": "C1",
    "command": "STOP",
    "payload": {}
  }
}
```

Command hợp lệ:

```text
STOP
RETURN_TO_KITCHEN
RESET_STATUS
```

## 7. Xác nhận command

Raspberry gửi sau khi đã chuyển command cho Arduino và xử lý xong:

```json
{
  "id": "7",
  "action": "acknowledge_command",
  "payload": {
    "command_id": "C1",
    "status": "DONE"
  }
}
```

Nếu lỗi:

```json
{
  "id": "7",
  "action": "acknowledge_command",
  "payload": {
    "command_id": "C1",
    "status": "FAILED"
  }
}
```

`status` chỉ nhận `DONE` hoặc `FAILED`
Response thành công:

```json
{
  "id": "7",
  "ok": true,
  "data": {
    "ok": true
  }
}
```

Response khi không tìm thấy command:

```json
{
  "id": "7",
  "ok": false,
  "error": "Không tìm thấy lệnh"
}
```