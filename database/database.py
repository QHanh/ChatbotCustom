import os
from sqlalchemy import Boolean, create_engine, Column, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import func
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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

class SessionControl(Base):
    __tablename__ = "session_controls"

    id = Column(String, primary_key=True, index=True)  # composite key: customer_id_session_id
    customer_id = Column(String, nullable=False, index=True)
    session_id = Column(String, nullable=False, index=True)
    session_name = Column(String, nullable=True)
    status = Column(String, nullable=False, default="active")  # active, stopped, human_chatting
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class CustomerisSale(Base):
    __tablename__ = "customer_is_sale"

    customer_id = Column(String, primary_key=True, index=True)
    thread_id = Column(String, nullable=False, index=True)
    is_sale = Column(Boolean, nullable=False, default=False)
    
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

def create_or_update_session_control(db: SessionLocal, customer_id: str, session_id: str, status: str, session_name: str = None):
    """Tạo mới hoặc cập nhật session control"""
    composite_id = f"{customer_id}_{session_id}"
    session_control = db.query(SessionControl).filter(SessionControl.id == composite_id).first()
    
    if session_control:
        session_control.status = status
        if session_name:
            session_control.session_name = session_name
    else:
        session_control = SessionControl(
            id=composite_id,
            customer_id=customer_id,
            session_id=session_id,
            session_name=session_name,
            status=status
        )
        db.add(session_control)
    
    db.commit()
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
