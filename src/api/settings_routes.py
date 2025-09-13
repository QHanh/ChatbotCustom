import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, Path, File, UploadFile
from sqlalchemy.orm import Session
from database.database import get_db, get_chatbot_settings, create_or_update_chatbot_settings
from src.models.schemas import ChatbotSettingsResponse, ChatbotSettingsCreate

router = APIRouter()

@router.get("/settings/{customer_id}", response_model=ChatbotSettingsResponse)
def read_chatbot_settings(
    customer_id: str = Path(..., title="Customer ID", description="The ID of the customer to retrieve settings for"),
    db: Session = Depends(get_db)
):
    """
    Retrieve chatbot settings for a specific customer.
    """
    settings = get_chatbot_settings(db, customer_id)
    if not settings:
        # Return default settings if none are found
        return ChatbotSettingsResponse()
    return settings

@router.post("/settings/{customer_id}", response_model=ChatbotSettingsResponse)
def create_or_update_settings(
    settings_data: ChatbotSettingsCreate,
    customer_id: str = Path(..., title="Customer ID", description="The ID of the customer to create or update settings for"),
    db: Session = Depends(get_db)
):
    """
    Create or update chatbot settings for a specific customer.
    """
    # Convert pydantic model to dict, excluding unset values to avoid overwriting with None
    update_data = settings_data.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No settings data provided")

    return create_or_update_chatbot_settings(db, customer_id, update_data)

@router.post("/settings/{customer_id}/upload-icon", response_model=ChatbotSettingsResponse)
def upload_chatbot_icon(
    customer_id: str = Path(..., title="Customer ID", description="The ID of the customer uploading the icon"),
    file: UploadFile = File(..., description="The icon image file to upload"),
    db: Session = Depends(get_db)
):
    """
    Upload a new icon for the chatbot, save it, and update the settings.
    """
    # Kiểm tra loại tệp
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File uploaded is not an image.")

    # Tạo thư mục nếu chưa tồn tại
    upload_dir = "JS_Chatbot/images"
    os.makedirs(upload_dir, exist_ok=True)

    # Lấy phần mở rộng tệp
    file_extension = os.path.splitext(file.filename)[1]
    if not file_extension:
        file_extension = ".png" # Mặc định nếu không có phần mở rộng

    # Tạo tên tệp mới và đường dẫn lưu
    new_filename = f"{customer_id}{file_extension}"
    file_path = os.path.join(upload_dir, new_filename)

    # Lưu tệp
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    # Cập nhật cơ sở dữ liệu
    # URL sẽ là đường dẫn tương đối, máy chủ sẽ xử lý phần còn lại
    icon_url = f"/images/{new_filename}"
    update_data = {"chatbot_icon_url": icon_url}
    
    return create_or_update_chatbot_settings(db, customer_id, update_data)
