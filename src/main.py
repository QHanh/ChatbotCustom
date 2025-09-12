from fastapi import FastAPI, Query, Depends, Form, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import threading
import time

from src.config.settings import APP_CONFIG, CORS_CONFIG
from src.models.schemas import ControlBotRequest
from src.api.chat_routes import chat_endpoint, HANDOVER_TIMEOUT, control_bot_endpoint, human_chatting_endpoint, power_off_bot_endpoint, get_session_controls_endpoint, get_chat_history_endpoint
from dependencies import init_es_client, close_es_client, get_db
from contextlib import asynccontextmanager
from src.api import upload_data_routes, info_store_routes
import logging
logging.getLogger("watchfiles").setLevel(logging.ERROR)
from sqlalchemy.orm import Session
from src.api import customer_is_sale_routes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Application startup...")
    try:
        print("📡 Initializing Elasticsearch client...")
        await init_es_client()
        print("✅ Elasticsearch initialization completed")
    except Exception as e:
        print(f"❌ Elasticsearch initialization failed: {e}")
    
    # Khởi động tác vụ nền để quét session timeout
    scanner_thread = threading.Thread(target=session_timeout_scanner, daemon=True)
    scanner_thread.start()
    print("Đã khởi động tác vụ nền để quét session timeout.")
    
    # init_db()
    yield
    print("🛑 Application shutdown...")
    try:
        await close_es_client()
        print("✅ Elasticsearch client closed")
    except Exception as e:
        print(f"❌ Error closing Elasticsearch client: {e}")

app = FastAPI(**APP_CONFIG, lifespan=lifespan)

app.add_middleware(CORSMiddleware, **CORS_CONFIG)

def session_timeout_scanner():
    """
    Quét và reset các session bị timeout trong một luồng nền.
    """
    from database.database import SessionLocal, create_or_update_session_control, get_sessions_for_timeout_check, add_chat_message
    
    while True:
        print("Chạy tác vụ nền: Quét các session timeout...")
        db = SessionLocal()
        try:
            sessions_to_check = get_sessions_for_timeout_check(db)
            current_time = time.time()
            
            for session in sessions_to_check:
                session_data = session.session_data or {}
                handover_time = session_data.get("handover_timestamp", 0)
                
                if (current_time - handover_time) > HANDOVER_TIMEOUT:
                    print(f"Session {session.id} đã quá hạn. Kích hoạt lại bot.")
                    
                    session_data["state"] = None
                    session_data["negativity_score"] = 0
                    
                    create_or_update_session_control(
                        db, 
                        customer_id=session.customer_id, 
                        session_id=session.session_id, 
                        status="active",
                        session_data=session_data
                    )
                    
                    add_chat_message(
                        db,
                        customer_id=session.customer_id,
                        thread_id=session.session_id,
                        role="bot",
                        message="Bot đã được tự động kích hoạt lại do không có hoạt động."
                    )
        except Exception as e:
            print(f"Lỗi trong tác vụ nền quét session timeout: {e}")
        finally:
            db.close()
        
        time.sleep(300)


app.include_router(upload_data_routes.router, tags=["Upload Data"])
app.include_router(info_store_routes.router, tags=["Info Store"])
app.include_router(customer_is_sale_routes.router)

@app.post("/chat/{customer_id}", summary="Gửi tin nhắn đến chatbot (hỗ trợ cả ảnh)")
async def chat(
    customer_id: str,
    db: Session = Depends(get_db),
    message: str = Form(""),
    model_choice: str = Form("gemini"),
    api_key: str = Form(...),
    session_id: str = Form("default", description="ID phiên chat"),
    image_url: str = Form(None, description="URL của hình ảnh (nếu có)"),
    image: UploadFile = File(None, description="File hình ảnh tải lên (nếu có)")
):
    """
    Endpoint chính để tương tác với chatbot. Hỗ trợ cả văn bản, URL ảnh và tải lên file ảnh.
    - **customer_id**: Mã của khách hàng (cửa hàng).
    - **message**: Câu hỏi của người dùng.
    - **session_id**: ID phiên chat.
    - **api_key**: Gemini API Key.
    - **image_url**: (Tùy chọn) Gửi URL của ảnh.
    - **image**: (Tùy chọn) Tải lên file ảnh.
    """
    if image_url and image:
        raise HTTPException(status_code=400, detail="Chỉ có thể cung cấp image_url hoặc tải lên file ảnh, không phải cả hai.")
        
    return await chat_endpoint(
        customer_id=customer_id,
        session_id=session_id,
        db=db,
        message=message,
        model_choice=model_choice,
        api_key=api_key,
        image_url=image_url,
        image=image
    )

@app.post("/control-bot/{customer_id}", summary="Dừng hoặc tiếp tục bot cho một session")
async def control_bot(
    customer_id: str,
    request: ControlBotRequest, 
    session_id: str = Query(..., description="ID phiên chat"),
    db: Session = Depends(get_db)
):
    """
    Endpoint để điều khiển bot.
    - **customer_id**: Mã khách hàng.
    - **command**: "start" để tiếp tục, "stop" để tạm dừng.
    - **session_id**: ID của phiên chat cần điều khiển.
    """
    return await control_bot_endpoint(request, customer_id, session_id, db)

@app.post("/human-chatting/{customer_id}", summary="Chuyển sang trạng thái human_chatting")
async def human_chatting(
    customer_id: str,
    session_id: str = Query(..., description="ID phiên chat"),
    db: Session = Depends(get_db)
):
    """
    Endpoint để chuyển sang trạng thái human_chatting.
    - **customer_id**: Mã khách hàng.
    - **session_id**: ID phiên chat cần chuyển sang trạng thái human_chatting.
    """
    return await human_chatting_endpoint(customer_id, session_id, db)

@app.post("/power-off-bot", summary="Stop or start the bot globally")
async def power_off_bot(request: ControlBotRequest):
    """
    Endpoint to control the bot globally.
    - **command**: "start" to continue, "stop" to pause.
    """
    return await power_off_bot_endpoint(request)

@app.get("/session-controls/{customer_id}", summary="Lấy danh sách session controls của customer")
async def get_session_controls(
    customer_id: str,
    db: Session = Depends(get_db)
):
    """
    Endpoint để lấy danh sách tất cả session controls của một customer.
    - **customer_id**: Mã khách hàng.
    """
    return await get_session_controls_endpoint(customer_id, db)

@app.get("/chat-history/{customer_id}/{session_id}", summary="Lấy lịch sử chat của một thread của một customer")
async def get_chat_history(
    customer_id: str,
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Endpoint để lấy toàn bộ lịch sử chat của một thread của một customer.
    - **customer_id**: Mã khách hàng.
    - **session_id**: ID của thread/session.
    """
    return await get_chat_history_endpoint(customer_id, session_id, db)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8018, reload=True)