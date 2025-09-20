from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database.database import Customer
from src.models.schemas import StoreInfo
from dependencies import get_db

router = APIRouter()

@router.post("/{customer_id}", response_model=StoreInfo, status_code=201)
def create_or_update_store_info(
    customer_id: str,
    store_info: StoreInfo,
    db: Session = Depends(get_db)
):
    """
    Tạo mới hoặc cập nhật thông tin cửa hàng cho một khách hàng.
    - **customer_id**: Mã khách hàng.
    - **Request body**: Thông tin chi tiết của cửa hàng.
    """
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    
    if customer:
        for key, value in store_info.model_dump(exclude_unset=True).items():
            setattr(customer, key, value)
    else:
        customer = Customer(customer_id=customer_id, **store_info.model_dump())
        db.add(customer)
        
    db.commit()
    db.refresh(customer)
    return customer

@router.get("/{customer_id}", response_model=StoreInfo)
def get_store_info(
    customer_id: str,
    db: Session = Depends(get_db)
):
    """
    Lấy thông tin cửa hàng của một khách hàng.
    - **customer_id**: Mã khách hàng.
    """
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy thông tin cho khách hàng '{customer_id}'")
    return customer

@router.get("/customers_info", response_model=List[StoreInfo])
def get_all_store_info(db: Session = Depends(get_db)):
    """
    Lấy thông tin của tất cả các cửa hàng.
    """
    customers = db.query(Customer).all()
    return [{"store_name": c.store_name, "store_address": c.store_address,
             "store_phone": c.store_phone, "store_email": c.store_email,
             "store_website": c.store_website, "store_facebook": c.store_facebook,
             "store_address_map": c.store_address_map, "store_image": c.store_image,
             "info_more": c.info_more} for c in customers]


@router.delete("/{customer_id}", status_code=204)
def delete_store_info(
    customer_id: str,
    db: Session = Depends(get_db)
):
    """
    Xóa thông tin cửa hàng của một khách hàng.
    - **customer_id**: Mã khách hàng.
    """
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy thông tin cho khách hàng '{customer_id}'")
    
    db.delete(customer)
    db.commit()
    return None
