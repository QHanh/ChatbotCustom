from pydantic import BaseModel, Field
from typing import List, Dict, Any, Literal, Optional

class BulkDeleteInput(BaseModel):
    """Input model for bulk delete operations."""
    ids: List[str] = Field(description="A list of document IDs to delete.")

class ControlBotRequest(BaseModel):
    command: str = Field(..., description="Lệnh điều khiển bot, ví dụ: 'start', 'stop'")

class ImageInfo(BaseModel):
    product_name: str
    image_url: str
    product_link: str

class PurchaseItem(BaseModel):
    product_name: str
    properties: Optional[str] = None
    quantity: int = 1

class CustomerInfo(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    items: List[PurchaseItem]

class Action(BaseModel):
    action: str
    url: str

class ChatResponse(BaseModel):
    reply: str
    history: List[Dict[str, str]]
    images: List[ImageInfo] = []
    has_images: bool = False
    has_purchase: bool = False
    customer_info: Optional[CustomerInfo] = None
    human_handover_required: Optional[bool] = False
    has_negativity: Optional[bool] = False
    action_data: Optional[Action] = None

class QueryExtraction(BaseModel):
    product_name: str
    category: str

class ProductRow(BaseModel):
    product_code: str
    product_name: str
    category: Optional[str] = None
    properties: Optional[str] = None
    lifecare_price: Optional[float] = None
    sale_price: Optional[float] = None
    trademark: Optional[str] = None
    guarantee: Optional[str] = None
    inventory: Optional[int] = None
    specifications: Optional[str] = None
    avatar_images: Optional[str] = None
    link_accessory: Optional[str] = None

class StoreInfo(BaseModel):
    store_name: Optional[str] = None
    store_address: Optional[str] = None
    store_phone: Optional[str] = None
    store_email: Optional[str] = None
    store_website: Optional[str] = None
    store_facebook: Optional[str] = None
    store_address_map: Optional[str] = None
    store_image: Optional[str] = None
    info_more: Optional[str] = None

    class Config:
        from_attributes = True

class CustomerIsSaleBase(BaseModel):
    customer_id: str
    thread_id: str
    is_sale: bool

class CustomerIsSaleCreate(CustomerIsSaleBase):
    pass

class CustomerIsSale(CustomerIsSaleBase):
    class Config:
        from_attributes = True

class ChatbotSettingsResponse(BaseModel):
    chatbot_icon_url: Optional[str] = None
    chatbot_message_default: Optional[str] = None
    chatbot_callout: Optional[str] = None
    chatbot_name: Optional[str] = None

    class Config:
        from_attributes = True

class ChatbotSettingsCreate(BaseModel):
    chatbot_icon_url: Optional[str] = None
    chatbot_message_default: Optional[str] = None
    chatbot_callout: Optional[str] = None
    chatbot_name: Optional[str] = None