from fastapi import APIRouter, Depends, HTTPException, Path, Body
from sqlalchemy.orm import Session

from dependencies import get_db
from database.database import (
    get_or_create_system_prompt, update_system_prompt, 
    get_or_create_general_prompt, update_general_prompt,
    get_combined_system_prompt
)
from src.models.schemas import SystemPromptResponse, SystemPromptUpdate

prompt_router = APIRouter()

# === GENERAL PROMPT ENDPOINTS (ADMIN CHỈNH) ===

@prompt_router.get("/general-prompt", response_model=SystemPromptResponse, summary="Get General System Prompt (Admin)")
def get_general_prompt(db: Session = Depends(get_db)):
    """
    Lấy general prompt (quy tắc 1-3) - chỉ admin mới chỉnh được.
    """
    prompt_content = get_or_create_general_prompt(db)
    if not prompt_content:
        raise HTTPException(status_code=404, detail="General prompt not found and could not be created.")
    return SystemPromptResponse(prompt_content=prompt_content)

@prompt_router.put("/general-prompt", response_model=SystemPromptResponse, summary="Update General System Prompt (Admin)")
def update_general_prompt_endpoint(
    prompt_data: SystemPromptUpdate = Body(...),
    db: Session = Depends(get_db)
):
    """
    Cập nhật general prompt (quy tắc 1-3) - chỉ admin mới chỉnh được.
    """
    updated_prompt = update_general_prompt(db, prompt_data.prompt_content)
    if not updated_prompt:
        raise HTTPException(status_code=500, detail="Failed to update the general prompt.")
    return SystemPromptResponse(prompt_content=updated_prompt.prompt_content)

@prompt_router.get("/prompts/{customer_id}", response_model=SystemPromptResponse, summary="Get Customer System Prompt (Customer chỉnh)")
def get_prompt(
    customer_id: str = Path(..., description="The ID of the customer"),
    db: Session = Depends(get_db)
):
    """
    Lấy system prompt của customer (quy tắc 4-14) - customer có thể chỉnh được.
    Nếu customer chưa có prompt, sẽ tự động tạo mới với nội dung mặc định.
    """
    prompt_content = get_or_create_system_prompt(db, customer_id)
    if not prompt_content:
        # This case should technically not be reached due to get_or_create logic
        raise HTTPException(status_code=404, detail="Prompt not found and could not be created.")
    return SystemPromptResponse(prompt_content=prompt_content)

@prompt_router.put("/prompts/{customer_id}", response_model=SystemPromptResponse, summary="Update System Prompt for a Customer")
def update_prompt(
    customer_id: str = Path(..., description="The ID of the customer"),
    prompt_data: SystemPromptUpdate = Body(...),
    db: Session = Depends(get_db)
):
    """
    Updates the system prompt for a specific customer.
    If the customer does not have a prompt, it will be created with the new content.
    """
    updated_prompt = update_system_prompt(db, customer_id, prompt_data.prompt_content)
    if not updated_prompt:
        raise HTTPException(status_code=500, detail="Failed to update the prompt.")
    return SystemPromptResponse(prompt_content=updated_prompt.prompt_content)

# === COMBINED PROMPT ENDPOINT ===

@prompt_router.get("/prompts/{customer_id}/combined", response_model=SystemPromptResponse, summary="Get Combined System Prompt")
def get_combined_prompt(
    customer_id: str = Path(..., description="The ID of the customer"),
    db: Session = Depends(get_db)
):
    """
    Lấy prompt đầy đủ (general + customer) - đây là prompt thực tế được sử dụng.
    """
    combined_prompt = get_combined_system_prompt(db, customer_id)
    if not combined_prompt:
        raise HTTPException(status_code=404, detail="Combined prompt could not be created.")
    return SystemPromptResponse(prompt_content=combined_prompt)
