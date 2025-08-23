import os
import requests
from src.config.settings import GEMINI_API_KEY, LMSTUDIO_API_URL, LMSTUDIO_MODEL, OPENAI_API_KEY
from typing import Optional
import io
from PIL import Image

def get_gemini_model(is_vision: bool = False):
    """Khởi tạo và trả về model Gemini."""
    if not GEMINI_API_KEY:
        print("Không tìm thấy GEMINI_API_KEY.")
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        if is_vision:
            model = genai.GenerativeModel('gemini-2.0-flash')
        else:
            model = genai.GenerativeModel('gemini-2.0-flash')
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

def analyze_image_with_vision(image_url: str) -> Optional[str]:
    """
    Sử dụng Gemini Pro Vision để phân tích và mô tả nội dung của một hình ảnh.
    """
    try:
        model = get_gemini_model(is_vision=True)
        if not model:
            print("Không thể khởi tạo model Gemini Vision.")
            return None

        print(f" -> Tải ảnh từ URL để phân tích: {image_url}")
        response = requests.get(image_url, timeout=15)
        response.raise_for_status()
        image_bytes = response.content
        
        image = Image.open(io.BytesIO(image_bytes))

        prompt = "Hãy mô tả ngắn gọn nội dung và mục đích của hình ảnh này bằng tiếng Việt. Tập trung vào việc xác định xem nó là sản phẩm, hóa đơn, biên lai chuyển khoản, hay một đoạn chat. Chỉ trả về nội dung mô tả, không thêm lời chào."
        
        print(" -> Gửi ảnh và prompt đến Gemini Vision...")
        response = model.generate_content([prompt, image])
        
        description = response.text.strip()
        return description

    except Exception as e:
        print(f"Lỗi trong quá trình phân tích ảnh bằng AI Vision: {e}")
        return None

def get_openai_model():
    """Khởi tạo và trả về client openai chuẩn >=1.0.0, hoặc None nếu thiếu key."""
    try:
        import openai
        if not OPENAI_API_KEY:
            return None
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        return client
    except Exception as e:
        print(f"Lỗi khi khởi tạo OpenAI client: {e}")
        return None