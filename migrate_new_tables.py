#!/usr/bin/env python3
"""
Migration script để tạo các bảng mới: CustomerProfile, Order, OrderItem
Chạy script này để cập nhật database schema.
"""

import sys
import os

# Thêm thư mục gốc vào Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import Base, engine, SessionLocal
from database.database import CustomerProfile, Order, OrderItem

def migrate_database():
    """Tạo các bảng mới trong database"""
    try:
        print("🚀 Bắt đầu migration database...")
        
        # Tạo tất cả bảng mới
        Base.metadata.create_all(bind=engine)
        
        print("✅ Migration thành công!")
        print("📋 Các bảng đã được tạo:")
        print("   - customer_profiles")
        print("   - orders") 
        print("   - order_items")
        
        # Kiểm tra kết nối database
        db = SessionLocal()
        try:
            # Test query để đảm bảo bảng đã được tạo
            profile_count = db.query(CustomerProfile).count()
            order_count = db.query(Order).count()
            item_count = db.query(OrderItem).count()
            
            print(f"📊 Trạng thái hiện tại:")
            print(f"   - Customer Profiles: {profile_count}")
            print(f"   - Orders: {order_count}")
            print(f"   - Order Items: {item_count}")
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Lỗi migration: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = migrate_database()
    if success:
        print("\n🎉 Migration hoàn tất! Bạn có thể sử dụng các bảng mới.")
    else:
        print("\n💥 Migration thất bại. Vui lòng kiểm tra lại.")
        sys.exit(1)
