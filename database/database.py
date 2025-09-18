import os
from sqlalchemy import Boolean, create_engine, Column, String, DateTime, Integer, Text, JSON, Float, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.sql import func
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def _make_json_safe(value):
    """Recursively convert non-JSON-serializable types (e.g., set) into JSON-safe ones."""
    if isinstance(value, set):
        return list(value)
    if isinstance(value, dict):
        return {k: _make_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_make_json_safe(v) for v in value]
    return value

class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(String, primary_key=True, index=True)
    store_name = Column(String, nullable=True)
    store_address = Column(String, nullable=True)
    store_phone = Column(String, nullable=True)
    store_email = Column(String, nullable=True)
    store_website = Column(String, nullable=True)
    store_facebook = Column(String, nullable=True)
    store_address_map = Column(String, nullable=True)
    store_image = Column(String, nullable=True)
    info_more = Column(String, nullable=True)

class ChatbotSettings(Base):
    __tablename__ = "chatbot_settings"

    customer_id = Column(String, primary_key=True, index=True)
    chatbot_icon_url = Column(String, nullable=True)
    chatbot_message_default = Column(String, nullable=True)
    chatbot_callout = Column(String, nullable=True)
    chatbot_name = Column(String, nullable=True)

class BotStatus(Base):
    __tablename__ = "bot_status"

    customer_id = Column(String, primary_key=True, index=True)
    status = Column(String, nullable=False, default="active")  # active, stopped
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class SessionControl(Base):
    __tablename__ = "session_controls"

    id = Column(String, primary_key=True, index=True)  # composite key: customer_id_session_id
    customer_id = Column(String, nullable=False, index=True)
    session_id = Column(String, nullable=False, index=True)
    session_name = Column(String, nullable=True)
    status = Column(String, nullable=False, default="active")  # active, stopped, human_chatting
    session_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class CustomerisSale(Base):
    __tablename__ = "customer_is_sale"

    customer_id = Column(String, primary_key=True, index=True)
    thread_id = Column(String, nullable=False, index=True)
    is_sale = Column(Boolean, nullable=False, default=False)
    
class ChatHistory(Base):
    __tablename__ = 'chat_history'

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(String, index=True, nullable=False)
    thread_id = Column(String, index=True, nullable=False)
    thread_name = Column(String, nullable=True)
    role = Column(String, nullable=False)  # 'user' or 'bot'
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class CustomerProfile(Base):
    __tablename__ = 'customer_profiles'

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(String, nullable=False, index=True)  # ID của cửa hàng
    session_id = Column(String, nullable=False, index=True)   # ID của session/thread
    name = Column(String, nullable=True)                      # Tên khách hàng
    phone = Column(String, nullable=True, index=True)         # Số điện thoại
    address = Column(Text, nullable=True)                     # Địa chỉ
    email = Column(String, nullable=True)                     # Email (tùy chọn)
    notes = Column(Text, nullable=True)                       # Ghi chú thêm
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship với orders
    orders = relationship("Order", back_populates="customer_profile")

class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True, index=True)
    customer_profile_id = Column(Integer, ForeignKey('customer_profiles.id'), nullable=False)
    customer_id = Column(String, nullable=False, index=True)  # ID của cửa hàng
    session_id = Column(String, nullable=False, index=True)   # ID của session/thread
    order_status = Column(String, nullable=False, default="pending")  # pending, confirmed, completed, cancelled
    total_amount = Column(Float, nullable=True)               # Tổng tiền (tùy chọn)
    notes = Column(Text, nullable=True)                       # Ghi chú đơn hàng
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    customer_profile = relationship("CustomerProfile", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = 'order_items'

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    product_name = Column(String, nullable=False)             # Tên sản phẩm
    properties = Column(String, nullable=True)                # Thuộc tính sản phẩm (màu sắc, kích thước, etc.)
    quantity = Column(Integer, nullable=False, default=1)     # Số lượng
    unit_price = Column(Float, nullable=True)                 # Giá đơn vị (tùy chọn)
    total_price = Column(Float, nullable=True)                # Tổng giá (tùy chọn)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    order = relationship("Order", back_populates="order_items")
    
def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper functions for SessionControl
def get_session_control(db: SessionLocal, customer_id: str, session_id: str):
    """Lấy thông tin session control từ database"""
    composite_id = f"{customer_id}_{session_id}"
    return db.query(SessionControl).filter(SessionControl.id == composite_id).first()

def create_or_update_session_control(db: SessionLocal, customer_id: str, session_id: str, status: str, session_name: str = None, session_data: dict = None):
    """Tạo mới hoặc cập nhật session control"""
    composite_id = f"{customer_id}_{session_id}"
    session_control = db.query(SessionControl).filter(SessionControl.id == composite_id).first()
    
    print(f"🔧 create_or_update_session_control: {composite_id}")
    print(f"   📊 Input status: {status}")
    print(f"   📊 Input session_data state: {session_data.get('state') if session_data else None}")
    
    if session_control:
        print(f"   📝 Updating existing session")
        print(f"   📝 Old status: {session_control.status}")
        print(f"   📝 Old session_data state: {session_control.session_data.get('state') if session_control.session_data else None}")
        
        session_control.status = status
        if session_name:
            session_control.session_name = session_name
        if session_data is not None:
            json_safe_data = _make_json_safe(session_data)
            print(f"   📝 JSON safe data state: {json_safe_data.get('state')}")
            session_control.session_data = json_safe_data
    else:
        print(f"   📝 Creating new session")
        json_safe_data = _make_json_safe(session_data) if session_data is not None else None
        print(f"   📝 JSON safe data state: {json_safe_data.get('state') if json_safe_data else None}")
        
        session_control = SessionControl(
            id=composite_id,
            customer_id=customer_id,
            session_id=session_id,
            session_name=session_name,
            status=status,
            session_data=json_safe_data
        )
        db.add(session_control)
    
    db.commit()
    db.refresh(session_control)
    
    print(f"   ✅ Final status in DB: {session_control.status}")
    print(f"   ✅ Final session_data state in DB: {session_control.session_data.get('state') if session_control.session_data else None}")
    
    return session_control

def get_all_session_controls_by_customer(db: SessionLocal, customer_id: str):
    """Lấy tất cả session controls của một customer"""
    return db.query(SessionControl).filter(SessionControl.customer_id == customer_id).all()

def delete_session_control(db: SessionLocal, customer_id: str, session_id: str):
    """Xóa session control"""
    composite_id = f"{customer_id}_{session_id}"
    session_control = db.query(SessionControl).filter(SessionControl.id == composite_id).first()
    if session_control:
        db.delete(session_control)
        db.commit()
        return True
    return False

# Helper functions for CustomerisSale
def get_customer_is_sale(db: SessionLocal, customer_id: str, thread_id: str):
    """Lấy thông tin is_sale của khách hàng"""
    return db.query(CustomerisSale).filter_by(customer_id=customer_id, thread_id=thread_id).first()

def create_or_update_customer_is_sale(db: SessionLocal, customer_id: str, thread_id: str, is_sale: bool):
    """Tạo mới hoặc cập nhật trạng thái is_sale của khách hàng"""
    customer_sale_info = get_customer_is_sale(db, customer_id, thread_id)
    
    if customer_sale_info:
        customer_sale_info.is_sale = is_sale
    else:
        customer_sale_info = CustomerisSale(
            customer_id=customer_id,
            thread_id=thread_id,
            is_sale=is_sale
        )
        db.add(customer_sale_info)
    
    db.commit()
    db.refresh(customer_sale_info)
    return customer_sale_info

def add_chat_message(db: SessionLocal, customer_id: str, thread_id: str, role: str, message: str, thread_name: str = None):
    """Thêm một tin nhắn vào lịch sử chat"""
    if not message or not message.strip():
        return
    chat_message = ChatHistory(
        customer_id=customer_id,
        thread_id=thread_id,
        thread_name=thread_name,
        role=role,
        message=message
    )
    db.add(chat_message)
    db.commit()
    db.refresh(chat_message)
    return chat_message

def get_chat_history(db: SessionLocal, customer_id: str, thread_id: str, limit: int = 20):
    """Lấy lịch sử chat từ database, sắp xếp theo thời gian gần nhất"""
    history_records = db.query(ChatHistory).filter(
        ChatHistory.customer_id == customer_id,
        ChatHistory.thread_id == thread_id
    ).order_by(ChatHistory.created_at.desc()).limit(limit).all()
    history_records.reverse()
    return history_records

def get_full_chat_history(db: SessionLocal, customer_id: str, thread_id: str):
    """Lấy toàn bộ lịch sử chat từ database, sắp xếp theo thời gian gần nhất."""
    return db.query(ChatHistory).filter(
        ChatHistory.customer_id == customer_id,
        ChatHistory.thread_id == thread_id
    ).order_by(ChatHistory.created_at.desc()).all()

def get_sessions_for_timeout_check(db: SessionLocal):
    """Lấy các session đang ở trạng thái cần handover để kiểm tra timeout."""
    # Lấy tất cả sessions có status là human_calling hoặc human_chatting
    sessions = db.query(SessionControl).filter(
        SessionControl.status.in_(["human_calling", "human_chatting"])
    ).all()
    
    # Filter thêm theo session_data.state nếu cần
    filtered_sessions = []
    if not sessions:
        sessions = db.query(SessionControl).all()
        for session in sessions:
            session_data = session.session_data or {}
            state = session_data.get("state")
            
            # Chỉ lấy sessions có state là human_calling hoặc human_chatting
            if state in ["human_calling", "human_chatting"]:
                filtered_sessions.append(session)
            else:
                print(f"⚠️ Session {session.id} có status={session.status} nhưng state={state}, bỏ qua")
    
    return filtered_sessions

# Helper functions for ChatbotSettings
def get_chatbot_settings(db: SessionLocal, customer_id: str):
    """Lấy thông tin cài đặt chatbot từ database"""
    return db.query(ChatbotSettings).filter(ChatbotSettings.customer_id == customer_id).first()

def create_or_update_chatbot_settings(db: SessionLocal, customer_id: str, settings_data: dict):
    """Tạo mới hoặc cập nhật cài đặt chatbot"""
    settings = db.query(ChatbotSettings).filter(ChatbotSettings.customer_id == customer_id).first()
    
    if settings:
        for key, value in settings_data.items():
            setattr(settings, key, value)
    else:
        settings = ChatbotSettings(
            customer_id=customer_id,
            **settings_data
        )
        db.add(settings)
    
    db.commit()
    db.refresh(settings)
    return settings

# Helper functions for CustomerProfile
def get_customer_profile(db: SessionLocal, customer_id: str, session_id: str = None, phone: str = None):
    """Lấy thông tin profile khách hàng theo customer_id và session_id hoặc phone"""
    query = db.query(CustomerProfile).filter(CustomerProfile.customer_id == customer_id)
    
    if session_id:
        query = query.filter(CustomerProfile.session_id == session_id)
    elif phone:
        query = query.filter(CustomerProfile.phone == phone)
    
    return query.first()

def get_customer_profile_by_phone(db: SessionLocal, customer_id: str, phone: str):
    """Tìm profile khách hàng theo số điện thoại trong cùng cửa hàng"""
    return db.query(CustomerProfile).filter(
        CustomerProfile.customer_id == customer_id,
        CustomerProfile.phone == phone
    ).first()

def create_or_update_customer_profile(db: SessionLocal, customer_id: str, session_id: str, 
                                    name: str = None, phone: str = None, address: str = None, 
                                    email: str = None, notes: str = None):
    """Tạo mới hoặc cập nhật profile khách hàng"""
    # Tìm profile hiện có theo session_id trước
    profile = get_customer_profile(db, customer_id, session_id)
    
    # Nếu không tìm thấy và có phone, tìm theo phone
    if not profile and phone:
        profile = get_customer_profile_by_phone(db, customer_id, phone)
        if profile:
            # Cập nhật session_id mới cho profile cũ
            profile.session_id = session_id
    
    if profile:
        # Cập nhật thông tin (chỉ cập nhật nếu có giá trị mới)
        if name and name.strip():
            profile.name = name
        if phone and phone.strip():
            profile.phone = phone
        if address and address.strip():
            profile.address = address
        if email and email.strip():
            profile.email = email
        if notes and notes.strip():
            profile.notes = notes
    else:
        # Tạo mới
        profile = CustomerProfile(
            customer_id=customer_id,
            session_id=session_id,
            name=name,
            phone=phone,
            address=address,
            email=email,
            notes=notes
        )
        db.add(profile)
    
    db.commit()
    db.refresh(profile)
    return profile

def has_previous_orders(db: SessionLocal, customer_id: str, phone: str = None, session_id: str = None):
    """Kiểm tra khách hàng đã từng đặt hàng chưa"""
    if phone:
        profile = get_customer_profile_by_phone(db, customer_id, phone)
    elif session_id:
        profile = get_customer_profile(db, customer_id, session_id)
    else:
        return False
    
    if not profile:
        return False
    
    # Kiểm tra có đơn hàng nào không
    order_count = db.query(Order).filter(Order.customer_profile_id == profile.id).count()
    return order_count > 0

# Helper functions for Order
def create_order(db: SessionLocal, customer_profile_id: int, customer_id: str, session_id: str,
                order_status: str = "pending", total_amount: float = None, notes: str = None):
    """Tạo đơn hàng mới"""
    order = Order(
        customer_profile_id=customer_profile_id,
        customer_id=customer_id,
        session_id=session_id,
        order_status=order_status,
        total_amount=total_amount,
        notes=notes
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order

def get_orders_by_customer_profile(db: SessionLocal, customer_profile_id: int):
    """Lấy tất cả đơn hàng của một customer profile"""
    return db.query(Order).filter(Order.customer_profile_id == customer_profile_id).order_by(Order.created_at.desc()).all()

def get_order_by_id(db: SessionLocal, order_id: int):
    """Lấy đơn hàng theo ID"""
    return db.query(Order).filter(Order.id == order_id).first()

def update_order_status(db: SessionLocal, order_id: int, status: str):
    """Cập nhật trạng thái đơn hàng"""
    order = get_order_by_id(db, order_id)
    if order:
        order.order_status = status
        db.commit()
        db.refresh(order)
    return order

# Helper functions for OrderItem
def add_order_item(db: SessionLocal, order_id: int, product_name: str, properties: str = None,
                  quantity: int = 1, unit_price: float = None, total_price: float = None):
    """Thêm sản phẩm vào đơn hàng"""
    order_item = OrderItem(
        order_id=order_id,
        product_name=product_name,
        properties=properties,
        quantity=quantity,
        unit_price=unit_price,
        total_price=total_price
    )
    db.add(order_item)
    db.commit()
    db.refresh(order_item)
    return order_item

def get_order_items(db: SessionLocal, order_id: int):
    """Lấy tất cả sản phẩm trong đơn hàng"""
    return db.query(OrderItem).filter(OrderItem.order_id == order_id).all()

def get_customer_order_history(db: SessionLocal, customer_id: str, phone: str = None, session_id: str = None):
    """Lấy lịch sử đơn hàng của khách hàng"""
    if phone:
        profile = get_customer_profile_by_phone(db, customer_id, phone)
    elif session_id:
        profile = get_customer_profile(db, customer_id, session_id)
    else:
        return []
    
    if not profile:
        return []
    
    return get_orders_by_customer_profile(db, profile.id)

# Helper functions for BotStatus
def get_bot_status(db: SessionLocal, customer_id: str):
    """Lấy trạng thái bot của customer"""
    return db.query(BotStatus).filter(BotStatus.customer_id == customer_id).first()

def create_or_update_bot_status(db: SessionLocal, customer_id: str, status: str):
    """Tạo mới hoặc cập nhật trạng thái bot của customer"""
    bot_status = get_bot_status(db, customer_id)
    
    if bot_status:
        bot_status.status = status
    else:
        bot_status = BotStatus(
            customer_id=customer_id,
            status=status
        )
        db.add(bot_status)
    
    db.commit()
    db.refresh(bot_status)
    return bot_status

def is_bot_active(db: SessionLocal, customer_id: str):
    """Kiểm tra bot có đang active không"""
    bot_status = get_bot_status(db, customer_id)
    if not bot_status:
        # Nếu chưa có record, mặc định là active
        return True
    return bot_status.status == "active"

def power_off_bot_for_customer(db: SessionLocal, customer_id: str):
    """Tắt bot cho customer (tất cả sessions)"""
    return create_or_update_bot_status(db, customer_id, "stopped")

def power_on_bot_for_customer(db: SessionLocal, customer_id: str):
    """Bật bot cho customer (tất cả sessions)"""
    return create_or_update_bot_status(db, customer_id, "active")
