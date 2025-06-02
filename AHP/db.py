# db.py
import psycopg2
import logging
from config import Config

def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            database=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD
        )
        logging.debug("Kết nối cơ sở dữ liệu thành công")
        return conn
    except Exception as e:
        logging.error(f"Lỗi khi kết nối cơ sở dữ liệu: {e}")
        return None
