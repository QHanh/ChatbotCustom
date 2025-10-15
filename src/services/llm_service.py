import os
import requests
import asyncio
from src.config.settings import LMSTUDIO_API_URL, LMSTUDIO_MODEL
from typing import Optional
import io
from PIL import Image

def get_gemini_model(is_vision: bool = False, api_key: str = None):
    """Khởi tạo và trả về model Gemini."""
    if not api_key:
        print("Không tìm thấy GEMINI_API_KEY.")
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model_name = 'gemini-2.0-flash'
        model = genai.GenerativeModel(model_name)
        return model
    except Exception as e:
        print(f"Lỗi khi khởi tạo Gemini: {e}")
        return None

def get_lmstudio_response(prompt: str):
    """Gửi prompt đến LM Studio API và nhận phản hồi."""
    try:
        url = f"{LMSTUDIO_API_URL}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        data = {
            "messages": [{"role": "user", "content": prompt}],
            "model": LMSTUDIO_MODEL,
            "temperature": 0.7,
            "max_tokens": 4000
        }
        
        print(f"Gửi yêu cầu đến LM Studio API: {url}")
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        result = response.json()
        
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        return "Không nhận được phản hồi từ LM Studio."
    except Exception as e:
        print(f"Lỗi khi gọi LM Studio: {e}")
        return None

def _blocking_generate_content(model, prompt: str, image: Image.Image) -> str:
    """Hàm đồng bộ để chạy generate_content trong một luồng riêng."""
    response = model.generate_content([prompt, image])
    return response.text.strip()

async def analyze_image_with_vision(image_url: str = None, image_bytes: bytes = None, api_key: str = None) -> Optional[str]:
    """
    Sử dụng Gemini Pro Vision để phân tích và mô tả nội dung của một hình ảnh (bất đồng bộ).
    """
    try:
        model = get_gemini_model(is_vision=True, api_key=api_key)
        if not model:
            print("Không thể khởi tạo model Gemini Vision.")
            return None

        # Ưu tiên sử dụng image_bytes nếu có sẵn
        if not image_bytes:
            if image_url:
                print(f" -> Tải ảnh từ URL để phân tích: {image_url}")
                # Sử dụng aiohttp hoặc chạy requests trong thread để không block
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, lambda: requests.get(image_url, timeout=15))
                response.raise_for_status()
                image_bytes = response.content
            else:
                return None # Không có nguồn ảnh
        
        if not image_bytes:
            return None
        
        image = Image.open(io.BytesIO(image_bytes))

        prompt = "Hãy mô tả ngắn gọn nội dung và mục đích của hình ảnh này bằng tiếng Việt. Tập trung vào việc xác định xem nó là sản phẩm, hóa đơn, biên lai chuyển khoản, hay một đoạn chat. Chỉ trả về nội dung mô tả kèm theo câu 'Khách hàng gửi một hình ảnh mô tả ...' ở đầu, không thêm lời chào."
        
        print(" -> Gửi ảnh và prompt đến Gemini Vision (async)...")
        
        # Chạy hàm blocking trong một luồng riêng
        description = await asyncio.to_thread(_blocking_generate_content, model, prompt, image)
        
        return description

    except Exception as e:
        print(f"Lỗi trong quá trình phân tích ảnh bằng AI Vision: {e}")
        return None

def get_openai_model(api_key: str = None):
    """Khởi tạo và trả về client openai chuẩn >=1.0.0, hoặc None nếu thiếu key."""
    try:
        import openai
        if not api_key:
            return None
        client = openai.OpenAI(api_key=api_key)
        return client
    except Exception as e:
        print(f"Lỗi khi khởi tạo OpenAI client: {e}")
        return None