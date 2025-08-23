from typing import List

def is_asking_for_more(user_query: str) -> bool:
    """Kiểm tra xem người dùng có muốn xem thêm sản phẩm không."""
    keywords = [
        "khác không", "nữa không", "thêm không", "loại nào nữa", "xem thêm", "mẫu nào không", "hết chưa", "còn không", 
        "mẫu nào khác", "sản phẩm nào khác", "loại khác", "loại nào khác", "nào nữa", "cái khác", "khác ko", "nữa ko", "còn ko", "hết chưa"
    ]
    return any(kw in user_query.lower() for kw in keywords)

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