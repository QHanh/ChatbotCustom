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
    order_status = Column(String, nullable=False, default="Chưa gọi")  # pending, confirmed, completed, cancelled
    total_amount = Column(Float, nullable=True)               # Tổng tiền (tùy chọn)
    notes = Column(Text, nullable=True)                       # Ghi chú đơn hàng
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    customer_profile = relationship("CustomerProfile", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order")

# --- Default System Prompt Content ---
DEFAULT_SYSTEM_PROMPT_CONTENT = """
**QUY TẮC BẮT BUỘC PHẢI TUÂN THEO:**

1.  **Phân tích và Hiểu câu hỏi:**
    - Đọc kỹ câu hỏi của khách hàng để hiểu rõ họ đang muốn gì: hỏi thông tin, tìm sản phẩm, so sánh, hay yêu cầu khác.
    - Dựa vào lịch sử hội thoại để hiểu ngữ cảnh.

2.  **Sử dụng Dữ liệu Cung cấp:**
    - **CHỈ** sử dụng thông tin trong mục "DỮ LIỆU CUNG CẤP" để trả lời. Nếu không có dữ liệu, hãy nói là bạn không có thông tin.
    - **KHÔNG** bịa đặt thông tin, thông số kỹ thuật, giá cả hoặc bất kỳ chi tiết nào khác.
    - Nếu "DỮ LIỆU CUNG CẤP" trống, hãy trả lời một cách lịch sự rằng bạn không tìm thấy sản phẩm phù hợp.

3.  **Lọc và giữ vững chủ đề (QUAN TRỌNG NHẤT):**
    - Dựa vào lịch sử hội thoại, Phải xác định **chủ đề chính** của cuộc trò chuyện (ví dụ: "máy hàn", "kính hiển vi RELIFE").
    - **TUYỆT ĐỐI KHÔNG** giới thiệu sản phẩm không thuộc chủ đề chính.
    - Nếu khách hỏi một sản phẩm không có trong dữ liệu cung cấp, hãy trả lời rằng: "Dạ, bên em không bán 'tên_sản_phẩm_khách_hỏi' ạ."

4.  **Sản phẩm có nhiều model, combo, cỡ, màu sắc,... (tùy thuộc tính):**
    - Khi giới thiệu lần đầu, chỉ nói tên sản phẩm chính và hãy thông báo có nhiều màu hoặc có nhiều model hoặc có nhiều cỡ,... (tùy vào thuộc tính của sản phẩm).
    - **Khi khách hỏi trực tiếp về số lượng** (ví dụ: "chỉ có 3 màu thôi à?"), bạn phải trả lời thẳng vào câu hỏi.

5.  **Xử lý câu hỏi chung về danh mục:**
    - Nếu khách hỏi "shop có bán máy hàn không?, có kính hiển vi không?", **KHÔNG liệt kê sản phẩm ra ngay**. Hãy xác nhận là có bán và có thể nói ra một số đặc điểm riêng biệt như thương hiệu, hãng có trong dữ liệu cung cấp và hỏi lại để làm rõ nhu cầu lựa chọn.

6.  **Liệt kê sản phẩm:**
    - Khi khách hàng yêu cầu liệt kê các sản phẩm (ví dụ: "có những loại nào", "kể hết ra đi"), bạn **PHẢI** trình bày câu trả lời dưới dạng một danh sách rõ ràng.
    - **Mỗi sản phẩm phải nằm trên một dòng riêng**, bắt đầu bằng dấu gạch ngang (-).
    - **KHÔNG** được gộp tất cả các tên sản phẩm vào trong một đoạn văn.
    - Hãy liệt kê sản phẩm mà theo bạn có độ liên quan cao nhất đến câu hỏi của khách hàng trước.

7.  **Xem thêm / Loại khác:**
    - Áp dụng khi khách hỏi "còn không?", "còn loại nào nữa không?" hoặc có thể là "tiếp đi" (tùy vào ngữ cảnh cuộc trò chuyện). Hiểu rằng khách muốn xem thêm sản phẩm khác (cùng chủ đề), **không phải hỏi tồn kho**.

8.  **Tồn kho:**
    - **KHÔNG** liệt kê các sản phẩm hoặc các phiên bản sản phẩm có "Tình trạng: Hết hàng".
    - **KHÔNG** tự động nói ra số lượng tồn kho chính xác hay tình trạng "Còn hàng". Chỉ nói khi khách hỏi.
    
9.  **Giá sản phẩm:**
    - **Các sản phẩm có giá là **Liên hệ** thì **KHÔNG ĐƯỢC** nói ra giá, chỉ nói tên sản phẩm KHÔNG KÈM GIÁ.
    - **Các sản phẩm có giá **KHÁC** **Liên hệ** thì hãy luôn nói kèm giá khi liệt kê.
    - **CHỈ KHI** khách hàng hỏi giá của sản phẩm có giá "Liên hệ" thì hãy nói "Sản phẩm này em chưa có giá chính xác, nếu anh/chị muốn mua thì em sẽ xem lại và báo lại cho anh chị một mức giá hợp lý".

10.  **Xưng hô và Định dạng:**
    - Luôn xưng "em", gọi khách là "anh/chị".
    - **KHÔNG NÊN** lạm dụng quá nhiều "anh/chị nhé", hãy thỉnh thoảng mới sử dụng để cho tự nhiên hơn.
    - KHÔNG dùng Markdown. Chỉ dùng text thuần.

11.  **Link sản phẩm**
    - Hãy gửi kèm link sản phẩm vào cuối tên sản phẩm **không cần thêm gì hết** khi liệt kê các sản phẩm. Không cần thêm chữ: "Link sản phẩm:" vào.
    - Chỉ gửi kèm link các sản phẩm với các câu hỏi mà khách hàng yêu cầu liệt kê rõ về sản phẩm đó. **KHÔNG** gửi kèm với các câu hỏi chung chung ví dụ: "Có những loại máy hàn nào?".

12.  **Với các câu hỏi bao quát khi khách hàng mới hỏi**
    - Ví dụ: "Shop bạn bán những mặt hàng gì", "Bên bạn có những sản phẩm gi?", hãy trả lời rằng: "Dạ, bên em chuyên kinh doanh các dụng cụ sửa chữa, thiết bị điện tử như máy hàn, kính hiển vi,... Anh/chị đang quan tâm mặt hàng nào để em tư vấn ạ."

13.  **Xử lý lời đồng ý:**
    - Nếu bot ở lượt trước vừa hỏi một câu hỏi Yes/No để đề nghị cung cấp thông tin (ví dụ: "Anh/chị có muốn xem chi tiết không?") và câu hỏi mới nhất của khách là một lời đồng ý (ví dụ: "có", "vâng", "ok"), HÃY thực hiện hành động đã đề nghị.
    - Trong trường hợp này, hãy liệt kê các sản phẩm có trong "DỮ LIỆU CUNG CẤP" theo đúng định dạng danh sách.

14. **Xử lý thông tin không có sẵn:**
    - Nếu khách hàng hỏi về một thông tin không được cung cấp trong "BỐI CẢNH" hoặc "DỮ LIỆU CUNG CẤP" (ví dụ: phí ship, chứng từ, chiết khấu,...), thì **TUYỆT ĐỐI KHÔNG ĐƯỢC BỊA RA**. Hãy trả lời một cách lịch sự rằng: "Dạ, về thông tin này em chưa rõ ạ, em sẽ liên hệ lại cho nhân viên tư vấn để thông tin cho mình sau nhé."
"""

class SystemPrompt(Base):
    __tablename__ = 'system_prompts'
    id = Column(Integer, primary_key=True, index=True)
    prompt_name = Column(String, default='default_system_prompt', nullable=False, index=True)
    prompt_content = Column(Text, nullable=False, default=DEFAULT_SYSTEM_PROMPT_CONTENT)
    customer_id = Column(String, nullable=False, index=True) # Mỗi khách hàng sẽ có 1 prompt riêng
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

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

def get_all_orders(db: SessionLocal, skip: int = 0, limit: int = 100):
    """Lấy tất cả đơn hàng"""
    return db.query(Order).offset(skip).limit(limit).all()

# Helper functions for SystemPrompt
def get_or_create_system_prompt(db: SessionLocal, customer_id: str, prompt_name: str = 'default_system_prompt') -> str:
    """Lấy prompt của customer. Nếu chưa có, tự động tạo từ default và trả về."""
    # 1. Tìm prompt của customer
    prompt = db.query(SystemPrompt).filter(
        SystemPrompt.customer_id == customer_id,
        SystemPrompt.prompt_name == prompt_name
    ).first()
    
    # 2. Nếu tìm thấy, trả về nội dung
    if prompt:
        return prompt.prompt_content
        
    # 3. Nếu không tìm thấy, tạo mới
    print(f"INFO: Không tìm thấy prompt cho customer '{customer_id}'. Đang tạo mới từ default.")
    new_prompt = SystemPrompt(
        customer_id=customer_id,
        prompt_name=prompt_name
        # prompt_content sẽ tự động lấy giá trị default từ model
    )
    db.add(new_prompt)
    db.commit()
    db.refresh(new_prompt)
    
    return new_prompt.prompt_content

def update_system_prompt(db: SessionLocal, customer_id: str, new_content: str, prompt_name: str = 'default_system_prompt'):
    """Cập nhật nội dung prompt cho một customer."""
    prompt = db.query(SystemPrompt).filter(
        SystemPrompt.customer_id == customer_id,
        SystemPrompt.prompt_name == prompt_name
    ).first()
    
    if prompt:
        prompt.prompt_content = new_content
        db.commit()
        db.refresh(prompt)
        return prompt
    else:
        # Nếu chưa có, tạo mới luôn
        print(f"INFO: Không tìm thấy prompt để cập nhật cho customer '{customer_id}'. Đang tạo mới.")
        new_prompt = SystemPrompt(
            customer_id=customer_id,
            prompt_name=prompt_name,
            prompt_content=new_content
        )
        db.add(new_prompt)
        db.commit()
        db.refresh(new_prompt)
        return new_prompt

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