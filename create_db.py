import os
import psycopg2
from urllib.parse import urlparse
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
from database.database import init_db

load_dotenv()

def create_database_if_not_exists():
    """
    Kết nối đến server PostgreSQL và tạo database nếu nó chưa tồn tại.
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Lỗi: Biến môi trường DATABASE_URL chưa được thiết lập.")
        return

    try:
        parsed_url = urlparse(db_url)
        db_name = parsed_url.path[1:]
        
        conn = psycopg2.connect(
            dbname="postgres",
            user=parsed_url.username,
            password=parsed_url.password,
            host=parsed_url.hostname,
            port=parsed_url.port
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
        exists = cursor.fetchone()
        
        if not exists:
            print(f"Database '{db_name}' chưa tồn tại. Đang tạo...")
            cursor.execute(f'CREATE DATABASE "{db_name}"')
            print(f"Đã tạo thành công database '{db_name}'.")
        else:
            print(f"Database '{db_name}' đã tồn tại.")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Đã xảy ra lỗi khi kiểm tra hoặc tạo database: {e}")
        exit(1)




if __name__ == "__main__":
    print("Đang khởi tạo database...")
    init_db()
    print("Database đã được khởi tạo thành công!")
    print("Các bảng đã được tạo:")
    print("- customers: Lưu thông tin cửa hàng")
    print("- session_controls: Lưu trạng thái các session")
