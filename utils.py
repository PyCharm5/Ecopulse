"""
Утилиты для работы с файлами и другими общими задачами
"""
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from typing import Optional, Tuple
from flask import current_app

def save_uploaded_file(file, prefix: str = 'file') -> Optional[str]:
    """
    Сохраняет загруженный файл и возвращает путь к нему
    """
    if not file or file.filename == '':
        return None
    
    try:
        # Генерируем безопасное имя файла
        timestamp = datetime.now().timestamp()
        ext = os.path.splitext(file.filename)[1] or '.jpg'
        filename = secure_filename(f"{prefix}_{timestamp}{ext}")
        
        # Сохраняем файл
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Возвращаем URL для доступа к файлу
        return f"/static/uploads/{filename}"
        
    except Exception as e:
        current_app.logger.error(f"Error saving uploaded file: {e}")
        return None


def get_coordinates_from_request(request) -> Tuple[float, float]:
    """
    Получает координаты из запроса или возвращает значения по умолчанию
    """
    try:
        lat = float(request.args.get('lat') or request.form.get('lat') or 
                   current_app.config.get('CITY_CENTER', [53.9925, 86.6669])[0])
        lng = float(request.args.get('lng') or request.form.get('lng') or 
                   current_app.config.get('CITY_CENTER', [53.9925, 86.6669])[1])
        return lat, lng
    except (ValueError, TypeError):
        # Возвращаем координаты по умолчанию (Киселевск)
        return 53.9925, 86.6669


def json_response(status: str = 'success', data: dict = None, 
                  message: str = '', code: int = 200) -> dict:
    """
    Стандартизированный ответ API
    """
    response = {'status': status}
    if data:
        response.update(data)
    if message:
        response['message'] = message
    return response, code


def is_valid_image_file(filename: str) -> bool:
    """
    Проверяет, является ли файл изображением по расширению
    """
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    ext = os.path.splitext(filename.lower())[1]
    return ext in allowed_extensions
