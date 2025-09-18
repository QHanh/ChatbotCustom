"""
Order Routes - API endpoints for managing customer orders
Chứa các API để quản lý đơn hàng của customers
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from dependencies import get_db
from database.database import (
    CustomerProfile, Order, OrderItem,
    get_customer_profile, get_customer_profile_by_phone,
    get_customer_order_history, get_orders_by_customer_profile
)

# Tạo router với tag
router = APIRouter(
    prefix="/orders",
    tags=["Order Management"],
    responses={404: {"description": "Not found"}}
)

async def get_orders_by_customer_endpoint(customer_id: str, db: Session, session_id: Optional[str] = None):
    """
    Lấy tất cả đơn hàng của customer_id.
    Có thể filter theo session_id nếu được cung cấp.
    """
    try:
        orders = []
        
        if session_id:
            # Lấy đơn hàng theo customer_id + session_id
            profile = get_customer_profile(db, customer_id, session_id)
            if profile:
                orders = get_orders_by_customer_profile(db, profile.id)
        else:
            # Lấy tất cả đơn hàng của customer_id (từ tất cả sessions)
            profiles = db.query(CustomerProfile).filter(
                CustomerProfile.customer_id == customer_id
            ).all()
            
            for profile in profiles:
                profile_orders = get_orders_by_customer_profile(db, profile.id)
                orders.extend(profile_orders)
        
        # Format response
        result = []
        for order in orders:
            # Lấy order items
            order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
            
            items_data = []
            for item in order_items:
                items_data.append({
                    "id": item.id,
                    "product_name": item.product_name,
                    "properties": item.properties,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "total_price": item.total_price,
                    "created_at": item.created_at.isoformat()
                })
            
            # Lấy thông tin customer profile
            profile = db.query(CustomerProfile).filter(CustomerProfile.id == order.customer_profile_id).first()
            
            order_data = {
                "id": order.id,
                "customer_profile_id": order.customer_profile_id,
                "customer_id": order.customer_id,
                "session_id": order.session_id,
                "order_status": order.order_status,
                "total_amount": order.total_amount,
                "notes": order.notes,
                "created_at": order.created_at.isoformat(),
                "updated_at": order.updated_at.isoformat() if order.updated_at else None,
                "customer_info": {
                    "name": profile.name if profile else None,
                    "phone": profile.phone if profile else None,
                    "address": profile.address if profile else None,
                    "email": profile.email if profile else None
                } if profile else None,
                "items": items_data,
                "total_items": len(items_data)
            }
            result.append(order_data)
        
        # Sắp xếp theo thời gian tạo (mới nhất trước)
        result.sort(key=lambda x: x["created_at"], reverse=True)
        
        return {
            "status": "success",
            "data": result,
            "total_orders": len(result),
            "customer_id": customer_id,
            "session_id": session_id
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Lỗi khi lấy đơn hàng: {str(e)}"}

async def get_order_by_id_endpoint(customer_id: str, order_id: int, db: Session):
    """
    Lấy chi tiết một đơn hàng cụ thể theo order_id và customer_id.
    """
    try:
        # Kiểm tra đơn hàng có thuộc về customer này không
        order = db.query(Order).filter(
            Order.id == order_id,
            Order.customer_id == customer_id
        ).first()
        
        if not order:
            return {
                "status": "error",
                "message": f"Không tìm thấy đơn hàng #{order_id} cho customer {customer_id}"
            }
        
        # Lấy order items
        order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        
        items_data = []
        total_quantity = 0
        for item in order_items:
            items_data.append({
                "id": item.id,
                "product_name": item.product_name,
                "properties": item.properties,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "total_price": item.total_price,
                "created_at": item.created_at.isoformat()
            })
            total_quantity += item.quantity
        
        # Lấy thông tin customer profile
        profile = db.query(CustomerProfile).filter(CustomerProfile.id == order.customer_profile_id).first()
        
        return {
            "status": "success",
            "data": {
                "id": order.id,
                "customer_profile_id": order.customer_profile_id,
                "customer_id": order.customer_id,
                "session_id": order.session_id,
                "order_status": order.order_status,
                "total_amount": order.total_amount,
                "notes": order.notes,
                "created_at": order.created_at.isoformat(),
                "updated_at": order.updated_at.isoformat() if order.updated_at else None,
                "customer_info": {
                    "name": profile.name if profile else None,
                    "phone": profile.phone if profile else None,
                    "address": profile.address if profile else None,
                    "email": profile.email if profile else None,
                    "notes": profile.notes if profile else None
                } if profile else None,
                "items": items_data,
                "total_items": len(items_data),
                "total_quantity": total_quantity
            }
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Lỗi khi lấy chi tiết đơn hàng: {str(e)}"}

async def get_orders_by_status_endpoint(customer_id: str, status: str, db: Session):
    """
    Lấy đơn hàng của customer theo trạng thái (pending, confirmed, completed, cancelled).
    """
    try:
        valid_statuses = ["pending", "confirmed", "completed", "cancelled"]
        if status not in valid_statuses:
            return {
                "status": "error",
                "message": f"Trạng thái không hợp lệ. Chỉ chấp nhận: {', '.join(valid_statuses)}"
            }
        
        # Lấy đơn hàng theo trạng thái
        orders = db.query(Order).filter(
            Order.customer_id == customer_id,
            Order.order_status == status
        ).order_by(Order.created_at.desc()).all()
        
        result = []
        for order in orders:
            # Lấy order items
            order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
            
            items_data = []
            for item in order_items:
                items_data.append({
                    "id": item.id,
                    "product_name": item.product_name,
                    "properties": item.properties,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "total_price": item.total_price
                })
            
            # Lấy thông tin customer profile
            profile = db.query(CustomerProfile).filter(CustomerProfile.id == order.customer_profile_id).first()
            
            order_data = {
                "id": order.id,
                "customer_id": order.customer_id,
                "session_id": order.session_id,
                "order_status": order.order_status,
                "total_amount": order.total_amount,
                "created_at": order.created_at.isoformat(),
                "customer_info": {
                    "name": profile.name if profile else None,
                    "phone": profile.phone if profile else None,
                    "address": profile.address if profile else None
                } if profile else None,
                "items": items_data,
                "total_items": len(items_data)
            }
            result.append(order_data)
        
        return {
            "status": "success",
            "data": result,
            "total_orders": len(result),
            "customer_id": customer_id,
            "filter_status": status
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Lỗi khi lấy đơn hàng theo trạng thái: {str(e)}"}

async def get_orders_summary_endpoint(customer_id: str, db: Session):
    """
    Lấy tóm tắt đơn hàng của customer (thống kê theo trạng thái).
    """
    try:
        # Đếm đơn hàng theo từng trạng thái
        pending_count = db.query(Order).filter(
            Order.customer_id == customer_id,
            Order.order_status == "pending"
        ).count()
        
        confirmed_count = db.query(Order).filter(
            Order.customer_id == customer_id,
            Order.order_status == "confirmed"
        ).count()
        
        completed_count = db.query(Order).filter(
            Order.customer_id == customer_id,
            Order.order_status == "completed"
        ).count()
        
        cancelled_count = db.query(Order).filter(
            Order.customer_id == customer_id,
            Order.order_status == "cancelled"
        ).count()
        
        total_orders = pending_count + confirmed_count + completed_count + cancelled_count
        
        # Lấy đơn hàng gần nhất
        latest_order = db.query(Order).filter(
            Order.customer_id == customer_id
        ).order_by(Order.created_at.desc()).first()
        
        # Tính tổng số sản phẩm đã bán
        total_items = db.query(OrderItem).join(Order).filter(
            Order.customer_id == customer_id
        ).count()
        
        return {
            "status": "success",
            "data": {
                "customer_id": customer_id,
                "total_orders": total_orders,
                "orders_by_status": {
                    "pending": pending_count,
                    "confirmed": confirmed_count,
                    "completed": completed_count,
                    "cancelled": cancelled_count
                },
                "total_items": total_items,
                "latest_order": {
                    "id": latest_order.id,
                    "created_at": latest_order.created_at.isoformat(),
                    "status": latest_order.order_status
                } if latest_order else None
            }
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Lỗi khi lấy tóm tắt đơn hàng: {str(e)}"}

async def update_order_status_endpoint(customer_id: str, order_id: int, new_status: str, db: Session):
    """
    Cập nhật trạng thái đơn hàng.
    """
    try:
        valid_statuses = ["pending", "confirmed", "completed", "cancelled"]
        if new_status not in valid_statuses:
            return {
                "status": "error",
                "message": f"Trạng thái không hợp lệ. Chỉ chấp nhận: {', '.join(valid_statuses)}"
            }
        
        # Tìm đơn hàng
        order = db.query(Order).filter(
            Order.id == order_id,
            Order.customer_id == customer_id
        ).first()
        
        if not order:
            return {
                "status": "error",
                "message": f"Không tìm thấy đơn hàng #{order_id} cho customer {customer_id}"
            }
        
        old_status = order.order_status
        order.order_status = new_status
        db.commit()
        
        return {
            "status": "success",
            "message": f"Đã cập nhật trạng thái đơn hàng #{order_id} từ '{old_status}' thành '{new_status}'",
            "data": {
                "order_id": order_id,
                "customer_id": customer_id,
                "old_status": old_status,
                "new_status": new_status,
                "updated_at": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": f"Lỗi khi cập nhật trạng thái đơn hàng: {str(e)}"}

# ==================== ROUTE DEFINITIONS ====================

@router.get("/{customer_id}", summary="Lấy tất cả đơn hàng của customer")
async def get_orders_by_customer(
    customer_id: str,
    session_id: str = Query(None, description="ID session để filter (tùy chọn)"),
    db: Session = Depends(get_db)
):
    """
    Endpoint để lấy tất cả đơn hàng của một customer.
    - **customer_id**: Mã khách hàng.
    - **session_id**: ID session để filter (tùy chọn). Nếu không cung cấp sẽ lấy tất cả đơn hàng.
    
    Returns:
    - Danh sách đơn hàng với thông tin chi tiết
    - Thông tin khách hàng và sản phẩm trong từng đơn hàng
    """
    return await get_orders_by_customer_endpoint(customer_id, db, session_id)

@router.get("/{customer_id}/{order_id}", summary="Lấy chi tiết một đơn hàng")
async def get_order_by_id(
    customer_id: str,
    order_id: int,
    db: Session = Depends(get_db)
):
    """
    Endpoint để lấy chi tiết một đơn hàng cụ thể.
    - **customer_id**: Mã khách hàng.
    - **order_id**: ID của đơn hàng cần xem chi tiết.
    
    Returns:
    - Thông tin chi tiết đơn hàng
    - Danh sách sản phẩm trong đơn hàng
    - Thông tin khách hàng
    """
    return await get_order_by_id_endpoint(customer_id, order_id, db)

@router.get("/{customer_id}/status/{status}", summary="Lấy đơn hàng theo trạng thái")
async def get_orders_by_status(
    customer_id: str,
    status: str,
    db: Session = Depends(get_db)
):
    """
    Endpoint để lấy đơn hàng theo trạng thái.
    - **customer_id**: Mã khách hàng.
    - **status**: Trạng thái đơn hàng (pending, confirmed, completed, cancelled).
    
    Returns:
    - Danh sách đơn hàng có trạng thái được chỉ định
    """
    return await get_orders_by_status_endpoint(customer_id, status, db)

@router.get("/{customer_id}/summary", summary="Lấy tóm tắt đơn hàng của customer")
async def get_orders_summary(
    customer_id: str,
    db: Session = Depends(get_db)
):
    """
    Endpoint để lấy tóm tắt đơn hàng của customer.
    - **customer_id**: Mã khách hàng.
    
    Returns:
    - Thống kê số lượng đơn hàng theo trạng thái
    - Tổng số đơn hàng và sản phẩm
    - Thông tin đơn hàng gần nhất
    """
    return await get_orders_summary_endpoint(customer_id, db)

@router.put("/{customer_id}/{order_id}/status", summary="Cập nhật trạng thái đơn hàng")
async def update_order_status(
    customer_id: str,
    order_id: int,
    new_status: str = Query(..., description="Trạng thái mới (pending, confirmed, completed, cancelled)"),
    db: Session = Depends(get_db)
):
    """
    Endpoint để cập nhật trạng thái đơn hàng.
    - **customer_id**: Mã khách hàng.
    - **order_id**: ID của đơn hàng cần cập nhật.
    - **new_status**: Trạng thái mới (pending, confirmed, completed, cancelled).
    
    Returns:
    - Thông tin về việc cập nhật trạng thái
    """
    return await update_order_status_endpoint(customer_id, order_id, new_status, db)
