import os

class Config:
    # --- БЕЗОПАСНОСТЬ ---
    # Секретный ключ для защиты сессий и cookies.
    # В продакшене (на реальном сервере) замените строку на случайный набор символов.
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'ecopulse-secret-key-2025-final-secure'
    
    # --- БАЗА ДАННЫХ ---
    # Используем SQLite для простоты. Файл будет создан в корне проекта.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///ecopulse_final.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # --- ЗАГРУЗКА ФАЙЛОВ ---
    # Папка, куда будут сохраняться фото проблем (создается автоматически в app.py)
    UPLOAD_FOLDER = os.path.join('static', 'uploads')
    # Максимальный размер загружаемого файла (16 Мегабайт)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    
    # --- API ПОГОДЫ И ЭКОЛОГИИ (OpenWeatherMap) ---
    # 1. Зарегистрируйтесь на https://home.openweathermap.org/users/sign_up
    # 2. Перейдите в раздел API Keys (https://home.openweathermap.org/api_keys)
    # 3. Скопируйте ваш Key и вставьте ниже вместо 'ВАШ_API_KEY_ЗДЕСЬ'
    # Если ключ не указан, сайт будет работать в демо-режиме (случайные данные).
    OPENWEATHER_API_KEY = '849eb3b74706b1536b82a112883337d3'
    
    # --- НАСТРОЙКИ ГОРОДА ПО УМОЛЧАНИЮ ---
    # Эти координаты используются, если пользователь не выбрал другой город
    # Координаты Киселевска
    CITY_NAME = 'Киселевск'
    CITY_CENTER = [53.9925, 86.6669]
    
    # --- ГЕЙМИФИКАЦИЯ ---
    # Количество баллов, начисляемых за действия
    POINTS_FOR_POINT = 15      # За создание заявки
    POINTS_FOR_LIKE = 5        # За лайк (если реализуете)
    POINTS_FOR_COMMENT = 10    # За комментарий
    POINTS_FOR_COMPLETION = 30 # За выполнение задания