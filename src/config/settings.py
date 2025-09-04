import os
from dotenv import load_dotenv
import json
import random

# Tải biến môi trường từ file .env
load_dotenv()

# Cấu hình chung
PAGE_SIZE = 10

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LMSTUDIO_API_URL = os.getenv("LMSTUDIO_API_URL")
LMSTUDIO_MODEL = os.getenv("LMSTUDIO_MODEL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELASTIC_HOST = os.getenv("ELASTIC_HOST")

# FastAPI Config
APP_CONFIG = {
    "title": "Chatbot Tư Vấn Bán Hàng",
    "description": "RAG Chatbot sử dụng Elasticsearch",
    "version": "1.2.0"
}

# CORS Config
CORS_CONFIG = {
    "allow_origins": ["*"],
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}