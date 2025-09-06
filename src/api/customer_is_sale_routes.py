from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.database import get_db, get_customer_is_sale, create_or_update_customer_is_sale
from src.models.schemas import CustomerIsSale, CustomerIsSaleCreate

router = APIRouter()

@router.post("/customer-is-sale", response_model=CustomerIsSale, tags=["Customer is Sale"])
async def set_customer_is_sale(
    customer_is_sale: CustomerIsSaleCreate,
    db: Session = Depends(get_db)
):
    """
    Tạo mới hoặc cập nhật trạng thái is_sale cho một khách hàng và thread_id cụ thể.
    """
    db_customer_is_sale = create_or_update_customer_is_sale(
        db=db,
        customer_id=customer_is_sale.customer_id,
        thread_id=customer_is_sale.thread_id,
        is_sale=customer_is_sale.is_sale
    )
    return db_customer_is_sale

@router.get("/customer-is-sale/{customer_id}/{thread_id}", response_model=CustomerIsSale, tags=["Customer is Sale"])
async def read_customer_is_sale(
    customer_id: str,
    thread_id: str,
    db: Session = Depends(get_db)
):
    """
    Lấy thông tin is_sale của một khách hàng dựa trên customer_id và thread_id.
    """
    db_customer_is_sale = get_customer_is_sale(db, customer_id, thread_id)
    if db_customer_is_sale is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông tin is_sale cho khách hàng.")
    return db_customer_is_sale
