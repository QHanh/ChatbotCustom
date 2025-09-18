#!/usr/bin/env python3
"""
Example usage của các bảng CustomerProfile, Order, OrderItem
Minh họa cách sử dụng trong chatbot system
"""

import sys
import os

# Thêm thư mục gốc vào Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import (
    SessionLocal, 
    create_or_update_customer_profile,
    has_previous_orders,
    create_order,
    add_order_item,
    get_customer_order_history,
    get_customer_profile_by_phone
)

def example_customer_flow():
    """Ví dụ flow xử lý khách hàng trong chatbot"""
    db = SessionLocal()
    
    try:
        print("=== DEMO CUSTOMER PROFILE & ORDER SYSTEM ===\n")
        
        # Thông tin demo
        customer_id = "shop123"
        session_id = "session_001"
        customer_name = "Nguyễn Văn A"
        customer_phone = "0123456789"
        customer_address = "123 Đường ABC, Quận 1, TP.HCM"
        
        # 1. Tạo profile khách hàng mới
        print("1. Tạo profile khách hàng mới...")
        profile = create_or_update_customer_profile(
            db=db,
            customer_id=customer_id,
            session_id=session_id,
            name=customer_name,
            phone=customer_phone,
            address=customer_address
        )
        print(f"   ✅ Profile ID: {profile.id}")
        print(f"   📞 Phone: {profile.phone}")
        print(f"   📍 Address: {profile.address}")
        
        # 2. Kiểm tra khách hàng cũ
        print("\n2. Kiểm tra khách hàng đã từng mua hàng chưa...")
        is_returning_customer = has_previous_orders(db, customer_id, phone=customer_phone)
        print(f"   🔍 Khách hàng cũ: {'Có' if is_returning_customer else 'Không'}")
        
        # 3. Tạo đơn hàng mới
        print("\n3. Tạo đơn hàng mới...")
        order = create_order(
            db=db,
            customer_profile_id=profile.id,
            customer_id=customer_id,
            session_id=session_id,
            order_status="pending",
            notes="Đơn hàng từ chatbot"
        )
        print(f"   ✅ Order ID: {order.id}")
        print(f"   📋 Status: {order.order_status}")
        
        # 4. Thêm sản phẩm vào đơn hàng
        print("\n4. Thêm sản phẩm vào đơn hàng...")
        
        # Sản phẩm 1
        item1 = add_order_item(
            db=db,
            order_id=order.id,
            product_name="iPhone 15 Pro",
            properties="Màu xanh, 128GB",
            quantity=1,
            unit_price=25000000.0
        )
        
        # Sản phẩm 2
        item2 = add_order_item(
            db=db,
            order_id=order.id,
            product_name="Ốp lưng iPhone",
            properties="Màu đen, silicon",
            quantity=2,
            unit_price=150000.0
        )
        
        print(f"   ✅ Đã thêm {item1.quantity}x {item1.product_name}")
        print(f"   ✅ Đã thêm {item2.quantity}x {item2.product_name}")
        
        # 5. Kiểm tra lại trạng thái khách hàng
        print("\n5. Kiểm tra lại sau khi có đơn hàng...")
        is_returning_customer_after = has_previous_orders(db, customer_id, phone=customer_phone)
        print(f"   🔍 Khách hàng cũ: {'Có' if is_returning_customer_after else 'Không'}")
        
        # 6. Lấy lịch sử đơn hàng
        print("\n6. Lịch sử đơn hàng của khách hàng...")
        order_history = get_customer_order_history(db, customer_id, phone=customer_phone)
        print(f"   📊 Tổng số đơn hàng: {len(order_history)}")
        
        for order in order_history:
            print(f"   📦 Order #{order.id} - {order.order_status} - {order.created_at}")
        
        # 7. Demo tìm khách hàng cũ trong session mới
        print("\n7. Demo khách hàng cũ vào session mới...")
        new_session_id = "session_002"
        
        # Tìm profile cũ theo phone
        existing_profile = get_customer_profile_by_phone(db, customer_id, customer_phone)
        if existing_profile:
            print(f"   🎯 Tìm thấy khách hàng cũ: {existing_profile.name}")
            print(f"   📞 Phone: {existing_profile.phone}")
            print(f"   📍 Address: {existing_profile.address}")
            
            # Cập nhật session_id mới
            updated_profile = create_or_update_customer_profile(
                db=db,
                customer_id=customer_id,
                session_id=new_session_id,
                phone=customer_phone  # Dùng phone để tìm profile cũ
            )
            print(f"   ✅ Đã cập nhật session_id: {updated_profile.session_id}")
        
        print("\n🎉 Demo hoàn tất!")
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        db.rollback()
    finally:
        db.close()

def example_chatbot_integration():
    """Ví dụ tích hợp vào chatbot flow"""
    print("\n=== CHATBOT INTEGRATION EXAMPLE ===")
    print("""
    Trong chat_routes.py, bạn có thể sử dụng như sau:
    
    # 1. Khi khách hàng cung cấp thông tin
    from database.database import create_or_update_customer_profile, has_previous_orders
    
    # Trích xuất thông tin từ tin nhắn
    extracted_info = extract_customer_info(user_query, model_choice, api_key=api_key)
    
    # Tạo/cập nhật profile
    profile = create_or_update_customer_profile(
        db=db,
        customer_id=customer_id,
        session_id=session_id,
        name=extracted_info.get('name'),
        phone=extracted_info.get('phone'),
        address=extracted_info.get('address')
    )
    
    # 2. Kiểm tra khách hàng cũ
    if extracted_info.get('phone'):
        is_returning = has_previous_orders(db, customer_id, phone=extracted_info['phone'])
        if is_returning:
            response_text = "Dạ, em nhận ra anh/chị là khách hàng quen của shop rồi ạ!"
    
    # 3. Tạo đơn hàng khi xác nhận mua
    if decision == "CONFIRM":
        order = create_order(
            db=db,
            customer_profile_id=profile.id,
            customer_id=customer_id,
            session_id=session_id,
            order_status="confirmed"
        )
        
        # Thêm sản phẩm vào đơn hàng
        for item in pending_items:
            add_order_item(
                db=db,
                order_id=order.id,
                product_name=item['product_name'],
                properties=item.get('properties'),
                quantity=item.get('quantity', 1)
            )
    """)

if __name__ == "__main__":
    example_customer_flow()
    example_chatbot_integration()
