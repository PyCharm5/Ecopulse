from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json
from datetime import datetime

# Инициализация объекта БД
db = SQLAlchemy()

class User(db.Model, UserMixin):
    """Модель пользователя системы"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    
    # Геймификация и статистика
    points = db.Column(db.Integer, default=0)       # Баллы ФМ
    level = db.Column(db.Integer, default=1)        # Уровень
    experience = db.Column(db.Integer, default=0)   # Опыт
    badges = db.Column(db.Text, default='[]')       # JSON строка со списком достижений
    
    # Роли и настройки профиля
    is_admin = db.Column(db.Boolean, default=False)
    is_worker = db.Column(db.Boolean, default=False) # Работник служб
    avatar = db.Column(db.String(500))               # Путь к файлу аватара
    city = db.Column(db.String(100), default='Киселевск')
    language = db.Column(db.String(10), default='ru')
    
    # Счетчики активности (для аналитики)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    total_reports = db.Column(db.Integer, default=0)
    total_completed = db.Column(db.Integer, default=0)
    total_points_added = db.Column(db.Integer, default=0)
    total_likes_given = db.Column(db.Integer, default=0)
    total_comments = db.Column(db.Integer, default=0)
    total_photos = db.Column(db.Integer, default=0)
    
    # Методы безопасности
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    # Работа с бейджами (храним как JSON список словарей)
    def add_badge(self, badge_name, badge_icon):
        try:
            badges_list = json.loads(self.badges)
        except:
            badges_list = []
        
        # Проверяем, есть ли уже такой бейдж, чтобы не дублировать
        if not any(b.get('name') == badge_name for b in badges_list):
            badge = {
                'name': badge_name,
                'icon': badge_icon,
                'earned_at': datetime.utcnow().isoformat()
            }
            badges_list.append(badge)
            self.badges = json.dumps(badges_list, ensure_ascii=False)
            return True
        return False
    
    def get_badges(self):
        try:
            return json.loads(self.badges)
        except:
            return []

class Problem(db.Model):
    """Модель проблемы/заявки на карте"""
    id = db.Column(db.Integer, primary_key=True)
    
    # Геоданные
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    
    # Описание
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    photo = db.Column(db.String(500))  # Путь к загруженному фото
    
    # Параметры классификации
    category = db.Column(db.String(50), default='other') # pollution, plants, water, etc.
    severity = db.Column(db.Integer, default=3)          # 1-5
    status = db.Column(db.String(20), default='reported') # reported, in_progress, completed, rejected
    reward = db.Column(db.Integer, default=15)           # Награда за выполнение
    
    # Связи с пользователями
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id')) # Кто взял в работу
    
    # Метаданные
    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Отношения (для удобного доступа через ORM)
    user = db.relationship('User', foreign_keys=[user_id], backref='reported_problems')
    worker = db.relationship('User', foreign_keys=[assigned_to], backref='assigned_problems')

class Complaint(db.Model):
    """Модель жалобы на контент"""
    id = db.Column(db.Integer, primary_key=True)
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id')) # Кто пожаловался
    
    reason = db.Column(db.String(100)) # spam, fake, offensive
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending') # pending, resolved, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    problem = db.relationship('Problem')
    user = db.relationship('User')

# --- Дополнительные модели (задел на будущее) ---

class SensorData(db.Model):
    """Хранение истории показаний датчиков"""
    id = db.Column(db.Integer, primary_key=True)
    sensor_id = db.Column(db.String(50))
    sensor_type = db.Column(db.String(50)) # temperature, humidity, air_quality
    value = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)