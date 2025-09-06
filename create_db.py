import os
import psycopg2
import argparse
from urllib.parse import urlparse
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
from database.database import init_db

load_dotenv()

def manage_database(recreate: bool = False):
    """
    Kết nối đến server PostgreSQL, tạo database nếu chưa có.
    Nếu recreate=True, sẽ xóa database cũ trước khi tạo lại.
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
        
        if exists:
            if recreate:
                print(f"Database '{db_name}' đã tồn tại. Đang xóa theo yêu cầu (--recreate)...")
                cursor.execute(f'DROP DATABASE "{db_name}"')
                print(f"Đã xóa database '{db_name}'.")
                # Sau khi xóa, coi như database không tồn tại để tạo lại ở bước sau
                exists = False
            else:
                print(f"Database '{db_name}' đã tồn tại. Bỏ qua việc tạo mới.")

        if not exists:
            print(f"Database '{db_name}' chưa tồn tại hoặc đã được xóa. Đang tạo...")
            cursor.execute(f'CREATE DATABASE "{db_name}"')
            print(f"Đã tạo thành công database '{db_name}'.")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Đã xảy ra lỗi khi quản lý database: {e}")
        exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Khởi tạo hoặc tạo lại database.")
    parser.add_argument("--recreate", action="store_true", help="Xóa database hiện tại và tạo lại từ đầu.")
    args = parser.parse_args()

    print("Đang khởi tạo database...")
    manage_database(recreate=args.recreate)
    init_db()
    print("Database đã được khởi tạo thành công!")
    print("Các bảng đã được tạo:")
    print("- customers: Lưu thông tin cửa hàng")
    print("- session_controls: Lưu trạng thái các session")
    print("- customer_is_sale: Lưu trạng thái sale của khách hàng")
