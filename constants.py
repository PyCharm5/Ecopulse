"""
Константы для всего приложения
"""

class ProblemStatus:
    """Статусы проблем"""
    REPORTED = 'reported'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    REJECTED = 'rejected'
    
    ALL = [REPORTED, IN_PROGRESS, COMPLETED, REJECTED]


class ProblemSeverity:
    """Уровни важности проблем"""
    VERY_LOW = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    VERY_HIGH = 5
    CRITICAL = 6
    
    # Цвета для отображения
    COLORS = {
        VERY_LOW: '#4CAF50',      # Зеленый
        LOW: '#27AE60',           # Зеленый темнее
        MEDIUM: '#F1C40F',        # Желтый
        HIGH: '#E67E22',          # Оранжевый
        VERY_HIGH: '#E74C3C',     # Красный
        CRITICAL: '#DC3522'       # Темно-красный
    }
    
    # Названия уровней
    NAMES = {
        VERY_LOW: 'Очень низкая',
        LOW: 'Низкая',
        MEDIUM: 'Средняя',
        HIGH: 'Высокая',
        VERY_HIGH: 'Очень высокая',
        CRITICAL: 'Критическая'
    }


class ProblemCategory:
    """Категории проблем"""
    OTHER = 'other'
    POLLUTION = 'pollution'
    PLANTS = 'plants'
    DAMAGE = 'damage'
    WATER = 'water'
    ANIMALS = 'animals'
    
    # Иконки для категорий
    ICONS = {
        OTHER: '⚠️',
        POLLUTION: '♻️',
        PLANTS: '🌿',
        DAMAGE: '🔨',
        WATER: '💧',
        ANIMALS: '🐕'
    }
    
    # Русские названия
    NAMES = {
        OTHER: 'Другое',
        POLLUTION: 'Мусор',
        PLANTS: 'Растения',
        DAMAGE: 'Поломка',
        WATER: 'Вода',
        ANIMALS: 'Животные'
    }


class OrderStatus:
    """Статусы заказов"""
    PENDING = 'pending'
    PROCESSING = 'processing'
    SHIPPED = 'shipped'
    DELIVERED = 'delivered'
    CANCELLED = 'cancelled'
    
    # Русские названия
    NAMES = {
        PENDING: 'Ожидает',
        PROCESSING: 'В обработке',
        SHIPPED: 'Отправлен',
        DELIVERED: 'Доставлен',
        CANCELLED: 'Отменен'
    }
    
    # Цвета для бейджей
    COLORS = {
        PENDING: 'warning',
        PROCESSING: 'info',
        SHIPPED: 'primary',
        DELIVERED: 'success',
        CANCELLED: 'danger'
    }


class ComplaintStatus:
    """Статусы жалоб"""
    PENDING = 'pending'
    RESOLVED = 'resolved'
    REJECTED = 'rejected'


class ConfigDefaults:
    """Значения по умолчанию из конфигурации"""
    POINTS_FOR_POINT = 15
    CITY_NAME = 'Киселевск'
    CITY_CENTER = [53.9925, 86.6669]  # Киселевск