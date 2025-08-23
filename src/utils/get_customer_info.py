from sqlalchemy.orm import Session
from database.database import Customer

def get_customer_store_info(db: Session, customer_id: str):
    """
    Lấy thông tin cửa hàng của một khách hàng từ database.
    """
    sanitized_id = customer_id.strip()
    customer = db.query(Customer).filter(Customer.customer_id == sanitized_id).first()
    if customer:
        return {
            "store_name": customer.store_name,
            "store_address": customer.store_address,
            "store_phone": customer.store_phone,
            "store_website": customer.store_website,
            "store_facebook": customer.store_facebook,
            "store_address_map": customer.store_address_map,
            "store_image": customer.store_image,
            "info_more": customer.info_more
        }
    return None
