import asyncio

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: dict[str, set[WebSocket]] = {}
        self._send_locks: dict[WebSocket, asyncio.Lock] = {}
        self._wakeups: dict[WebSocket, asyncio.Event] = {}

    async def connect(self, websocket: WebSocket, robot_id: str) -> None:
        await websocket.accept()
        self.active_connections.setdefault(robot_id, set()).add(websocket)
        self._send_locks[websocket] = asyncio.Lock()
        self._wakeups[websocket] = asyncio.Event()

    def disconnect(self, websocket: WebSocket, robot_id: str) -> None:
        connections = self.active_connections.get(robot_id)
        if connections:
            connections.discard(websocket)
            if not connections:
                self.active_connections.pop(robot_id, None)
        self._send_locks.pop(websocket, None)
        self._wakeups.pop(websocket, None)

    def is_online(self, robot_id: str) -> bool:
        return bool(self.active_connections.get(robot_id))

    def online_robot_ids(self) -> set[str]:
        return set(self.active_connections)

    async def send_json(self, websocket: WebSocket, message: dict) -> None:
        async with self._send_locks[websocket]:
            await websocket.send_json(message)

    def notify_commands(self, robot_id: str) -> bool:
        """Đánh thức vòng lặp đẩy lệnh. True nếu robot đang online ở process này."""
        sockets = self.active_connections.get(robot_id, ())
        for ws in sockets:
            event = self._wakeups.get(ws)
            if event:
                event.set()
        return bool(sockets)

    async def wait_for_wakeup(self, websocket: WebSocket, timeout: float) -> None:
        event = self._wakeups.get(websocket)
        if event is None:
            await asyncio.sleep(timeout)
            return
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass
        finally:
            event.clear()


manager = ConnectionManager()