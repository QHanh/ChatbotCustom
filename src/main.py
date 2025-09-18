from fastapi import FastAPI, Query, Depends, Form, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import threading
import time

from src.config.settings import APP_CONFIG, CORS_CONFIG
from src.models.schemas import ControlBotRequest
from src.api.chat_routes import chat_endpoint, HANDOVER_TIMEOUT, control_bot_endpoint, human_chatting_endpoint, power_off_bot_endpoint, get_session_controls_endpoint, get_chat_history_endpoint
from dependencies import init_es_client, close_es_client, get_db
from src.api.chat_routes import power_off_bot_customer_endpoint, get_bot_status_endpoint, delete_chat_history_endpoint
from src.api.order_routes import router as order_router
from contextlib import asynccontextmanager
from src.api import upload_data_routes, info_store_routes, settings_routes
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

# Phục vụ các tệp tĩnh từ thư mục JS_Chatbot/images
app.mount("/images", StaticFiles(directory="JS_Chatbot/images"), name="images")

def session_timeout_scanner():
    """
    Quét và reset các session bị timeout trong một luồng nền.
    """
    from database.database import SessionLocal, get_sessions_for_timeout_check, add_chat_message
    from src.api.chat_routes import _update_session_state
    
    while True:
        print("Chạy tác vụ nền: Quét các session timeout...")
        db = SessionLocal()
        try:
            sessions_to_check = get_sessions_for_timeout_check(db)
            current_time = time.time()
            
            print(f"📊 Found {len(sessions_to_check)} sessions to check for timeout")
            
            for session in sessions_to_check:
                session_data = session.session_data or {}
                handover_time = session_data.get("handover_timestamp")
                state = session_data.get("state")
                
                print(f"🔍 Checking session {session.id}:")
                print(f"   - Customer: {session.customer_id}")
                print(f"   - Session ID: {session.session_id}")
                print(f"   - Status: {session.status}")
                print(f"   - State: {state}")
                print(f"   - Handover timestamp: {handover_time}")
                
                # Fix 1: Kiểm tra handover_timestamp có tồn tại và hợp lệ không
                if handover_time is None or handover_time == 0:
                    print(f"   ❌ Handover timestamp không hợp lệ, bỏ qua session này")
                    continue
                
                # Debug: In thông tin thời gian
                elapsed_time = current_time - handover_time
                print(f"   ⏰ Thời gian:")
                print(f"      - Handover time: {handover_time}")
                print(f"      - Current time: {current_time}")
                print(f"      - Elapsed: {elapsed_time:.2f}s ({elapsed_time/60:.2f} phút)")
                print(f"      - Timeout threshold: {HANDOVER_TIMEOUT}s ({HANDOVER_TIMEOUT/60:.2f} phút)")
                
                # Fix 2: Kiểm tra timeout với handover_timestamp hợp lệ
                if elapsed_time > HANDOVER_TIMEOUT:
                    print(f"   ✅ Session đã quá hạn, reset về active")
                    
                    # Fix 3: Sử dụng _update_session_state để đảm bảo sync đúng
                    _update_session_state(db, session.customer_id, session.session_id, "active", session_data)
                    
                    # Thêm tin nhắn thông báo
                    add_chat_message(
                        db,
                        customer_id=session.customer_id,
                        thread_id=session.session_id,
                        role="bot",
                        message="Bot đã được tự động kích hoạt lại do không có hoạt động từ nhân viên trong 15 phút."
                    )
                    
                    print(f"✅ Session {session.id} đã được reset về active.")
                else:
                    print(f"   ⏳ Session chưa quá hạn, còn {(HANDOVER_TIMEOUT - elapsed_time)/60:.2f} phút")
                    
        except Exception as e:
            print(f"Lỗi trong tác vụ nền quét session timeout: {e}")
        finally:
            db.close()
        
        time.sleep(300)


app.include_router(upload_data_routes.router, tags=["Upload Data"])
app.include_router(info_store_routes.router, tags=["Info Store"])
app.include_router(customer_is_sale_routes.router)
app.include_router(settings_routes.router, tags=["Chatbot Settings"])
app.include_router(order_router)

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

@app.post("/power-off-bot/{customer_id}", summary="Stop or start the bot for a specific customer")
async def power_off_bot_customer(
    customer_id: str,
    request: ControlBotRequest,
    db: Session = Depends(get_db)
):
    """
    Endpoint to control the bot for a specific customer.
    - **customer_id**: Mã khách hàng cần điều khiển bot.
    - **command**: "start" để kích hoạt, "stop" để tạm dừng, "status" để kiểm tra trạng thái.
    """
    return await power_off_bot_customer_endpoint(customer_id, request, db)

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

@app.get("/bot-status/{customer_id}", summary="Lấy trạng thái bot của customer")
async def get_bot_status(
    customer_id: str,
    db: Session = Depends(get_db)
):
    """
    Endpoint để lấy trạng thái bot của một customer cụ thể.
    - **customer_id**: Mã khách hàng cần kiểm tra trạng thái bot.
    
    Returns:
    - **bot_status**: "active" hoặc "stopped"
    - **is_active**: True/False
    - **created_at**: Thời gian tạo record (nếu có)
    - **updated_at**: Thời gian cập nhật gần nhất (nếu có)
    """
    return await get_bot_status_endpoint(customer_id, db)

@app.delete("/chat-history/{customer_id}/{session_id}", summary="Xóa lịch sử chat của session")
async def delete_chat_history(
    customer_id: str,
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Endpoint để xóa toàn bộ lịch sử chat của một session cụ thể.
    - **customer_id**: Mã khách hàng.
    - **session_id**: ID của session/thread cần xóa lịch sử.
    
    Returns:
    - **deleted_messages**: Số lượng tin nhắn đã xóa
    - Đồng thời reset session data về trạng thái ban đầu
    """
    return await delete_chat_history_endpoint(customer_id, session_id, db)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8018, reload=True)