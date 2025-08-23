# Chatbot Tư Vấn Bán Hàng

Ứng dụng chatbot RAG tư vấn bán hàng sử dụng Elasticsearch.

## Tính năng

- Tìm kiếm sản phẩm thông minh với Elasticsearch
- Hỗ trợ: Google Gemini, LM Studio, OpenAI
- Giao diện Streamlit
- Phân tích ý định người dùng

## Cài đặt

1. Cài đặt các thư viện cần thiết:

```bash
pip install -r requirements.txt
```

2. Cấu hình API key trong file `.env`:

```
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```
## Đẩy dữ liệu vào Elasticsearch

1. Cài đặt Elasticsearch:

```bash
docker-compose up -build
```

2. Chạy script đẩy dữ liệu vào Elasticsearch:

```bash
python elastic_search_push_data.py
```
## Chạy ứng dụng

1. Khởi động backend FastAPI:

```bash
python app.py
```

2. Khởi động frontend Streamlit:

```bash
streamlit run ui-test.py
```

## Sử dụng LM Studio

1. Tải và cài đặt LM Studio từ [trang chủ](https://lmstudio.ai/)
2. Cấu hình URL và model trong file `.env`:

```
LMSTUDIO_API_URL=your_lmstudio_api_url_here
LMSTUDIO_MODEL=your_lmstudio_model_here
```

3. Trong giao diện Streamlit, chọn "LM Studio" trong sidebar

## Cấu trúc dự án

- `app.py`: Backend FastAPI
- `ui-test.py`: Frontend Streamlit
- `elastic_search_push_data.py`: Kết nối và đẩy dữ liệu vào Elasticsearch
- `requirements.txt`: Danh sách thư viện cần thiết

## Lưu ý

- Đảm bảo Elasticsearch đang chạy trước khi khởi động ứng dụng