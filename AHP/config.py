# config.py
import os

class Config:
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
    DB_HOST = 'localhost'
    DB_PORT = 5432
    DB_NAME = 'ahp'
    DB_USER = 'postgres'
    DB_PASSWORD = '12345'

    @staticmethod
    def init_app(app):
        if not os.path.exists(Config.UPLOAD_FOLDER):
            os.makedirs(Config.UPLOAD_FOLDER)
