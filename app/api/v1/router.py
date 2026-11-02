"""
app/api/v1/router.py
----------------------
Gộp tất cả router con (5 nhóm chức năng) thành 1 router duy nhất cho version 1.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import admin, auth, billing, categories, dishes, orders, tables
from app.api.v1.endpoints import admin, auth, dishes, hardware, orders, robot_admin
from app.api.v1.endpoints import admin, auth, dishes, hardware, orders

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(billing.router)
api_router.include_router(categories.router)
api_router.include_router(dishes.router)
api_router.include_router(dishes.admin_router)
api_router.include_router(orders.router)
api_router.include_router(orders.public_router)
api_router.include_router(orders.staff_router)
api_router.include_router(tables.router)
api_router.include_router(tables.public_router)
api_router.include_router(hardware.router)
api_router.include_router(hardware.hardware_router)
api_router.include_router(robot_admin.router)
