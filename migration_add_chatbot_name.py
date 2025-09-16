import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Tải các biến môi trường từ tệp .env
load_dotenv()

# Lấy URL cơ sở dữ liệu từ biến môi trường
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("Lỗi: Biến môi trường DATABASE_URL chưa được đặt.")
else:
    try:
        # Tạo kết nối đến cơ sở dữ liệu
        engine = create_engine(DATABASE_URL)
        
        # Câu lệnh SQL để thêm cột mới
        # Lệnh này sẽ không thành công nếu cột đã tồn tại, điều này an toàn.
        alter_table_sql = text("ALTER TABLE chatbot_settings ADD COLUMN chatbot_name VARCHAR")

        with engine.connect() as connection:
            print("Đang kết nối đến cơ sở dữ liệu...")
            connection.execute(alter_table_sql)
            print("Thành công! Cột 'chatbot_name' đã được thêm vào bảng 'chatbot_settings'.")

    except Exception as e:
        print(f"Đã xảy ra lỗi: {e}")
        print("Có thể cột 'chatbot_name' đã tồn tại trong bảng 'chatbot_settings'.")
