from typing import List
import json
import re
from typing import List

from src.services.llm_service import get_gemini_model


def is_asking_for_more(user_query: str, history_text: str, api_key: str = None) -> bool:
    """
    Sử dụng AI để xác định xem người dùng có muốn xem thêm sản phẩm hay không,
    phân biệt với việc hỏi về tồn kho.
    """
    prompt = f"""
    Bạn là một AI chuyên phân tích ý định của khách hàng.
    Nhiệm vụ của bạn là đọc cuộc trò chuyện và xác định ý định của khách hàng trong câu hỏi cuối cùng.

    ## Bối cảnh hội thoại:
    {history_text}
    Câu hỏi mới nhất của khách hàng: "{user_query}"

    ## Phân tích và quyết định:
    Hãy phân loại ý định của khách hàng vào MỘT trong ba loại sau:
    1.  **MORE_PRODUCTS**: Khách hàng muốn xem thêm các sản phẩm khác, các loại khác, các mẫu mã khác.
        - Ví dụ: "còn loại nào khác không?", "xem thêm mẫu", "có cái nào nữa không?", "tiếp đi", "còn không?" (khi ngữ cảnh đang là liệt kê sản phẩm).
    2.  **ASKING_INVENTORY**: Khách hàng đang hỏi về tình trạng tồn kho của một sản phẩm cụ thể đã được đề cập.
        - Ví dụ: "sản phẩm này còn hàng không?", "còn hàng không shop?", "còn ko?" (khi ngữ cảnh đang nói về 1 sản phẩm).
    3.  **OTHER**: Câu hỏi không thuộc hai loại trên.

    ## QUY TẮC PHÂN LOẠI (RẤT QUAN TRỌNG) ##

    1.  **Khi nào là `MORE_PRODUCTS`?**
        - CHỈ khi BỐI CẢNH cho thấy bot vừa liệt kê một danh sách sản phẩm (ví dụ: "Bên em có các loại máy hàn A, B, C..."), VÀ câu hỏi mới nhất của khách là một yêu cầu **tiếp tục danh sách đó**.
        - Các câu hỏi mẫu: "còn không?", "còn loại nào nữa không?", "tiếp đi", "xem thêm", "kể tiếp đi".
        - Ý định này là để **lật trang (pagination)** xem các sản phẩm **cùng loại** đã được tìm kiếm trước đó.

    2.  **Khi nào KHÔNG PHẢI là `MORE_PRODUCTS`? (Sẽ là `OTHER`)**
        - Nếu câu hỏi của khách hàng **giới thiệu một chủ đề hoặc loại sản phẩm mới** không có trong cuộc trò chuyện gần đây.
        - **VÍ DỤ QUAN TRỌNG:** Nếu bot đang nói về "máy hàn", và khách hỏi "em tham khảo thêm cái giá đỡ và bộ đèn", đây là một yêu cầu tìm kiếm mới, KHÔNG PHẢI `MORE_PRODUCTS`.
        - Nếu câu hỏi của khách hàng là một câu hỏi chung chung về sản phẩm mà không có ngữ cảnh liệt kê trước đó (ví dụ: "bên shop có những sản phẩm nào?").
        - Nếu câu hỏi của khách hàng là "kể hết ra" nhưng bot chưa liệt kê sản phẩm nào cả.
        - Xin tất cả ảnh, xin ảnh nhiều loại không phải là `MORE_PRODUCTS`.

    3.  **Khi nào là `ASKING_INVENTORY`?**
        - Khi cuộc trò chuyện đang tập trung vào MỘT sản phẩm cụ thể và khách hàng hỏi "còn hàng không?", "còn không?".

    Hãy trả về kết quả dưới dạng một đối tượng JSON duy nhất với cấu trúc:
    {{"intent": "MORE_PRODUCTS" | "ASKING_INVENTORY" | "OTHER"}}

    JSON kết quả:
    """

    try:
        model = get_gemini_model(api_key=api_key)
        if model:
            from google.generativeai.types import GenerationConfig
            generation_config = GenerationConfig(response_mime_type="application/json")
            response = model.generate_content(prompt, generation_config=generation_config)
            
            data = json.loads(response.text)
            intent = data.get("intent", "OTHER").upper()
            
            print(f"AI đánh giá ý định 'xem thêm': {intent}")
            
            if intent == "MORE_PRODUCTS":
                return True
    
    except Exception as e:
        print(f"Lỗi khi AI đánh giá ý định 'xem thêm': {e}")

    # Fallback an toàn là False
    return False

def is_general_query(user_query: str) -> bool:
    """Kiểm tra xem có phải câu hỏi chung chung về sản phẩm không."""
    general_queries = [
        "shop có những sản phẩm nào", "shop đang kinh doanh gì", "cửa hàng bán những gì"
    ]
    return any(kw in user_query.lower() for kw in general_queries)

def format_history_text(history: List[dict], limit: int = 10) -> str:
    """Format lịch sử hội thoại thành text."""
    if not history:
        return ""
    
    history_text = ""
    for turn in history[-limit:]:
        history_text += f"Khách: {turn['user']}\nBot: {turn['bot']}\n"
    return history_text

def sanitize_for_es(text: str) -> str:
    """Làm sạch text để sử dụng trong Elasticsearch."""
    return text.replace("-", "")