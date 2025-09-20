from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from dependencies import get_db
from database.database import get_or_create_system_prompt, update_system_prompt
from src.models.schemas import SystemPromptResponse, SystemPromptUpdate

prompt_router = APIRouter()

@prompt_router.get("/prompts/{customer_id}", response_model=SystemPromptResponse, summary="Get System Prompt for a Customer")
def get_prompt(
    customer_id: str = Path(..., description="The ID of the customer"),
    db: Session = Depends(get_db)
):
    """
    Retrieves the system prompt for a specific customer.
    If the customer does not have a prompt, a new one will be created with the default content.
    """
    prompt_content = get_or_create_system_prompt(db, customer_id)
    if not prompt_content:
        # This case should technically not be reached due to get_or_create logic
        raise HTTPException(status_code=404, detail="Prompt not found and could not be created.")
    return SystemPromptResponse(prompt_content=prompt_content)

@prompt_router.put("/prompts/{customer_id}", response_model=SystemPromptResponse, summary="Update System Prompt for a Customer")
def update_prompt(
    customer_id: str = Path(..., description="The ID of the customer"),
    prompt_data: SystemPromptUpdate = Depends(),
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
