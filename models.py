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
    
    # Реферальная система
    referral_code = db.Column(db.String(20), unique=True)
    referred_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    referral_points = db.Column(db.Integer, default=0)
    
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

    def check_achievements(self):
        """Проверка и начисление достижений"""
        achievements = []
        
        # Проверяем достижения (без заказов, чтобы избежать циклического импорта)
        if self.total_reports >= 1 and not self.has_achievement('Первая проблема'):
            self.add_badge('Первая проблема', 'fa-map-marker-alt')
            achievements.append('Первая проблема')
        
        if self.total_reports >= 10 and not self.has_achievement('10 проблем'):
            self.add_badge('10 проблем', 'fa-flag')
            achievements.append('10 проблем')
        
        if self.total_completed >= 5 and not self.has_achievement('5 решений'):
            self.add_badge('5 решений', 'fa-check-circle')
            achievements.append('5 решений')
        
        if self.points >= 500 and not self.has_achievement('Богатый волонтер'):
            self.add_badge('Богатый волонтер', 'fa-coins')
            achievements.append('Богатый волонтер')
        
        if self.experience >= 1000 and not self.has_achievement('Опытный волонтер'):
            self.add_badge('Опытный волонтер', 'fa-star')
            achievements.append('Опытный волонтер')
        
        # Проверка заказов будет выполняться отдельно при создании заказа
        return achievements

    def has_achievement(self, name):
        """Проверить, есть ли достижение"""
        badges = self.get_badges()
        return any(b.get('name') == name for b in badges)

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
    status = db.Column(db.String(20), default='reported') # reported, assigned, in_progress, completed, rejected
    reward = db.Column(db.Integer, default=15)           # Награда за выполнение
    
    # Голосование
    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)
    
    # Связи с пользователями
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id')) # Кто взял в работу
    completed_by = db.Column(db.Integer, db.ForeignKey('user.id')) # Кто выполнил
    
    # Статус выполнения
    is_completed = db.Column(db.Boolean, default=False)  # Выполнена ли задача
    
    # Метаданные
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    assigned_at = db.Column(db.DateTime)  # Когда взяли в работу
    completed_at = db.Column(db.DateTime)  # Когда выполнили
    
    # Отношения (для удобного доступа через ORM)
    user = db.relationship('User', foreign_keys=[user_id], backref='reported_problems')
    worker = db.relationship('User', foreign_keys=[assigned_to], backref='assigned_problems')
    completer = db.relationship('User', foreign_keys=[completed_by], backref='completed_problems')
    comments = db.relationship('Comment', backref='problem_comment', cascade='all,delete')
    task_completion = db.relationship('TaskCompletion', backref='problem_report', uselist=False, cascade='all,delete')

class Comment(db.Model):
    """Модель комментария к проблеме"""
    id = db.Column(db.Integer, primary_key=True)
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Отношения
    user = db.relationship('User', backref='user_comments')

class Complaint(db.Model):
    """Модель жалобы на контент"""
    id = db.Column(db.Integer, primary_key=True)
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id')) # Кто пожаловался
    
    reason = db.Column(db.String(100)) # spam, fake, offensive, duplicate, other
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending') # pending, resolved, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Новые поля для обработки жалоб
    resolved_at = db.Column(db.DateTime)
    resolved_by = db.Column(db.Integer, db.ForeignKey('user.id')) # Кто обработал
    action_taken = db.Column(db.String(50)) # problem_deleted, user_warned, complaint_rejected, no_action
    admin_comment = db.Column(db.Text) # Комментарий админа при обработке
    
    problem = db.relationship('Problem', backref='complaints')
    user = db.relationship('User', foreign_keys=[user_id], backref='user_complaints')
    admin = db.relationship('User', foreign_keys=[resolved_by], backref='resolved_complaints')
    
class TaskCompletion(db.Model):
    """Модель фотоотчета о выполнении задания"""
    id = db.Column(db.Integer, primary_key=True)
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Фото "Было" и "Стало"
    before_photo = db.Column(db.String(500))
    after_photo = db.Column(db.String(500))
    
    # Описание проделанной работы
    description = db.Column(db.Text)
    
    # Рейтинг выполнения (от администратора или других пользователей)
    rating = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Отношения
    user = db.relationship('User', backref='task_completions')
    # проблема уже связана через problem_report

class Order(db.Model):
    """Модель заказа из магазина"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    item_id = db.Column(db.Integer)  # ID товара из магазина
    item_name = db.Column(db.String(200))
    price = db.Column(db.Integer)
    quantity = db.Column(db.Integer, default=1)
    
    # Данные доставки
    address = db.Column(db.Text)
    phone = db.Column(db.String(20))
    size = db.Column(db.String(10))
    comment = db.Column(db.Text)
    
    # Статус заказа
    status = db.Column(db.String(20), default='pending')  # pending, processing, shipped, delivered, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    # Отношения
    user = db.relationship('User', backref='user_orders')

class Vote(db.Model):
    """Модель голосования (лайки/дизлайки)"""
    id = db.Column(db.Integer, primary_key=True)
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    vote_type = db.Column(db.String(10))  # 'like' или 'dislike'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Уникальный индекс для предотвращения множественных голосов
    __table_args__ = (db.UniqueConstraint('problem_id', 'user_id', name='unique_vote'),)
    
    # Отношения
    user = db.relationship('User', backref='user_votes')
    problem = db.relationship('Problem', backref='problem_votes')

# --- Дополнительные модели (задел на будущее) ---

class SensorData(db.Model):
    """Хранение истории показаний датчиков"""
    id = db.Column(db.Integer, primary_key=True)
    sensor_id = db.Column(db.String(50))
    sensor_type = db.Column(db.String(50)) # temperature, humidity, air_quality
    value = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
