from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import requests
import random
import secrets
import json

# Импорт конфигурации и моделей
from config import Config
from models import db, User, Problem, Complaint, Comment, TaskCompletion, Order, Vote, SensorData

# Импорт новых модулей
from decorators import admin_required
from constants import ProblemStatus, ProblemSeverity, ProblemCategory, OrderStatus, ComplaintStatus, ConfigDefaults
from utils import save_uploaded_file, get_coordinates_from_request, json_response, is_valid_image_file

app = Flask(__name__)
app.config.from_object(Config)

# Инициализация расширений
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Создание папки для загрузок, если нет
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@login_manager.user_loader
def load_user(user_id: int) -> User:
    return User.query.get(int(user_id))

@app.context_processor
def inject_global_vars():
    return {
        'current_user': current_user,
        'now': datetime.utcnow(),
        'ProblemStatus': ProblemStatus,
        'ProblemSeverity': ProblemSeverity,
        'ProblemCategory': ProblemCategory,
        'OrderStatus': OrderStatus
    }

# ==========================================
# РОУТЫ СТРАНИЦ (РЕНДЕРИНГ)
# ==========================================

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/map')
@login_required
def map_view():
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    users = User.query.all()
    problems = Problem.query.all()
    complaints = Complaint.query.filter_by(status=ComplaintStatus.PENDING).all()
    tasks = Problem.query.filter(Problem.status != ProblemStatus.COMPLETED).all()
    
    total_points = sum(u.points for u in users)
    new_points_today = sum(1 for p in problems if p.created_at.date() == datetime.utcnow().date())
    
    return render_template('admin.html',
                         users=users,
                         problems=problems,
                         points=problems, # Для совместимости с разными шаблонами
                         complaints=complaints,
                         tasks=tasks,
                         total_users=len(users),
                         total_points=total_points,
                         total_tasks=len(tasks),
                         new_points_today=new_points_today)

@app.route('/admin/profile')
@login_required
@admin_required
def admin_profile_view():
    """Отдельная страница управления для админа (из admin_profile.html)"""
    users = User.query.all()
    problems = Problem.query.all()
    complaints = Complaint.query.filter_by(status=ComplaintStatus.PENDING).all()
    
    return render_template('admin_profile.html',
                         users=users,
                         problems=problems,
                         complaints=complaints)

@app.route('/profile')
@login_required
def profile():
    # Мои проблемы (сортировка по новизне)
    my_reports = Problem.query.filter_by(user_id=current_user.id).order_by(Problem.created_at.desc()).all()
    # Выполненные мной задания
    my_completed = Problem.query.filter_by(assigned_to=current_user.id, status=ProblemStatus.COMPLETED).order_by(Problem.completed_at.desc()).all()
    
    # Расчет рейтинга
    all_users = User.query.order_by(User.points.desc()).all()
    user_rank = next((i + 1 for i, u in enumerate(all_users) if u.id == current_user.id), 0)
    
    return render_template('profile.html', 
                         my_reports=my_reports, 
                         my_completed=my_completed,
                         user_rank=user_rank)

@app.route('/dashboard')
@login_required
def dashboard():
    recent_points = Problem.query.filter_by(user_id=current_user.id).order_by(Problem.created_at.desc()).limit(5).all()
    user_tasks = Problem.query.filter_by(assigned_to=current_user.id, status=ProblemStatus.IN_PROGRESS).all()
    user_badges = current_user.get_badges()
    achievements = [] # Здесь можно добавить логику проверки достижений
    
    return render_template('dashboard.html',
                         user=current_user,
                         recent_points=recent_points,
                         user_tasks=user_tasks,
                         user_badges=user_badges,
                         achievements=achievements)

@app.route('/tasks')
@login_required
def tasks():
    # Доступные задания: статус reported и никто не взял
    available_tasks = Problem.query.filter_by(status=ProblemStatus.REPORTED, assigned_to=None).all()
    # Мои текущие задания
    my_tasks = Problem.query.filter_by(assigned_to=current_user.id, status=ProblemStatus.IN_PROGRESS).all()
    
    return render_template('tasks.html', tasks=available_tasks, my_tasks=my_tasks)

@app.route('/completed_tasks')
@login_required
def completed_tasks():
    """Страница выполненных заданий с фотоотчетами"""
    # Все завершенные проблемы с отчетами
    completed = Problem.query.filter_by(status=ProblemStatus.COMPLETED).all()
    
    # Собираем отчеты
    reports = []
    for problem in completed:
        report = TaskCompletion.query.filter_by(problem_id=problem.id).first()
        reports.append({
            'problem': problem,
            'report': report,
            'user': problem.worker if problem.assigned_to else None
        })
    
    return render_template('completed_tasks.html', reports=reports)

@app.route('/rating')
@login_required
def rating():
    users = User.query.order_by(User.points.desc()).limit(50).all()
    return render_template('rating.html', users=users)

@app.route('/shop')
@login_required
def shop():
    items = [
        {'id': 1, 'name': 'Футболка Экопульс', 'price': 150, 'image': '/static/shop/tshirt.png'},
        {'id': 2, 'name': 'Кружка с логотипом', 'price': 80, 'image': '/static/shop/mug.png'},
        {'id': 3, 'name': 'Эко-сумка', 'price': 120, 'image': '/static/shop/bag.png'},
        {'id': 4, 'name': 'Термос', 'price': 200, 'image': '/static/shop/thermos.png'},
        {'id': 5, 'name': 'Блокнот волонтера', 'price': 50, 'image': '/static/shop/notebook.png'},
        {'id': 6, 'name': 'Ручка из переработки', 'price': 30, 'image': '/static/shop/pen.png'},
    ]
    return render_template('shop.html', items=items)

@app.route('/education')
@login_required
def education():
    return render_template('education.html')

@app.route('/analytics')
@login_required
def analytics():
    problems = Problem.query.all()
    users = User.query.all()
    
    total_points = len(problems)
    active_points = len([p for p in problems if p.status != ProblemStatus.COMPLETED])
    completed_points = len([p for p in problems if p.status == ProblemStatus.COMPLETED])
    
    active_users = sorted(users, key=lambda u: u.total_reports, reverse=True)[:5]
    
    categories = {}
    for p in problems:
        categories[p.category] = categories.get(p.category, 0) + 1
        
    priorities = {
        'Критический': len([p for p in problems if p.severity >= 5]),
        'Высокий': len([p for p in problems if p.severity == 4]),
        'Средний': len([p for p in problems if p.severity == 3]),
        'Низкий': len([p for p in problems if p.severity <= 2])
    }

    # Берем город из конфига или дефолтный
    city_name = app.config.get('CITY_NAME', ConfigDefaults.CITY_NAME)

    return render_template('analytics.html',
                         city_name=city_name,
                         total_points=total_points,
                         active_points=active_points,
                         completed_points=completed_points,
                         active_users=active_users,
                         categories=categories,
                         priorities=priorities,
                         points=problems)

# ==========================================
# АВТОРИЗАЦИЯ
# ==========================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        
        flash('Неверное имя пользователя или пароль', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует', 'error')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        
        # Генерируем реферальный код
        user.referral_code = secrets.token_urlsafe(8)[:10]
        
        # Проверяем реферальный код из формы
        ref_code = request.form.get('ref_code')
        if ref_code:
            referrer = User.query.filter_by(referral_code=ref_code).first()
            if referrer:
                user.referred_by = referrer.id
                referrer.referral_points += 50  # Награда за приглашение
                referrer.points += 50
        
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return redirect(url_for('index'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ==========================================
# API ЭНДПОИНТЫ
# ==========================================

@app.route('/api/problems', methods=['GET'])
@login_required
def get_problems_api():
    """Получение списка активных проблем для карты"""
    # Показываем только не завершенные, или все (зависит от логики, тут все кроме скрытых)
    problems = Problem.query.filter(Problem.status != ProblemStatus.COMPLETED).all()
    result = []
    for p in problems:
        result.append({
            'id': p.id,
            'lat': p.lat,
            'lng': p.lng,
            'title': p.title,
            'description': p.description,
            'category': p.category,
            'severity': p.severity,
            'reward': p.reward,
            'status': p.status,
            'photo': p.photo, # URL фото
            'likes': p.likes,
            'dislikes': p.dislikes
        })
    return jsonify(result)

@app.route('/api/problems/add', methods=['POST'])
@login_required
def add_problem():
    """Добавление проблемы с фото"""
    try:
        title = request.form.get('title')
        lat = float(request.form.get('lat'))
        lng = float(request.form.get('lng'))
        description = request.form.get('description', '')
        category = request.form.get('category', ProblemCategory.OTHER)
        severity = int(request.form.get('severity', ProblemSeverity.MEDIUM))
        
        # Обработка файла с использованием новой утилиты
        photo_path = save_uploaded_file(request.files.get('photo'), prefix='prob')
        
        problem = Problem(
            lat=lat, lng=lng,
            title=title,
            description=description,
            category=category,
            severity=severity,
            photo=photo_path,
            user_id=current_user.id,
            reward=app.config.get('POINTS_FOR_POINT', ConfigDefaults.POINTS_FOR_POINT),
            status=ProblemStatus.REPORTED
        )
        
        # Начисляем опыт и баллы создателю
        points_to_add = app.config.get('POINTS_FOR_POINT', ConfigDefaults.POINTS_FOR_POINT)
        current_user.points += points_to_add
        current_user.total_reports += 1
        current_user.experience += 30
        
        # Проверяем достижения
        current_user.check_achievements()
        
        db.session.add(problem)
        db.session.commit()
        
        return json_response('success', {'id': problem.id}, 'Проблема добавлена')
    except Exception as e:
        app.logger.error(f"Error adding problem: {e}")
        return json_response('error', {}, f'Ошибка при добавлении: {str(e)}', 500)

@app.route('/api/problems/<int:problem_id>/take', methods=['POST'])
@login_required
def take_problem(problem_id: int):
    """Взять задание в работу"""
    problem = Problem.query.get_or_404(problem_id)
    
    if problem.assigned_to:
        return json_response('error', {}, 'Задание уже занято', 400)
    
    problem.assigned_to = current_user.id
    problem.status = ProblemStatus.IN_PROGRESS
    db.session.commit()
    return json_response('success', {}, 'Задание принято')

@app.route('/api/problems/<int:problem_id>/cancel', methods=['POST'])
@login_required
def cancel_problem(problem_id: int):
    """Отменить взятое задание"""
    problem = Problem.query.get_or_404(problem_id)
    
    if problem.assigned_to != current_user.id:
        return json_response('error', {}, 'Вы не выполняете это задание', 403)
    
    if problem.status != ProblemStatus.IN_PROGRESS:
        return json_response('error', {}, 'Задание не в работе', 400)
    
    problem.assigned_to = None
    problem.status = ProblemStatus.REPORTED
    db.session.commit()
    
    return json_response('success', {}, 'Задание отменено')

@app.route('/api/problems/<int:problem_id>/complete', methods=['POST'])
@login_required
def complete_problem(problem_id: int):
    """Отметить задание выполненным"""
    problem = Problem.query.get_or_404(problem_id)
    
    # Проверка прав (либо автор, либо исполнитель, либо админ)
    if not (current_user.id == problem.assigned_to or current_user.is_admin):
        return json_response('error', {}, 'Нет прав', 403)

    if problem.status == ProblemStatus.COMPLETED:
        return json_response('error', {}, 'Уже выполнено', 400)
        
    problem.status = ProblemStatus.COMPLETED
    problem.completed_at = datetime.utcnow()
    
    # Начисляем награду тому, кто выполнил (или текущему юзеру, если он закрыл)
    current_user.points += problem.reward
    current_user.total_completed += 1
    current_user.experience += 50
    
    # Проверяем достижения
    current_user.check_achievements()
    
    db.session.commit()
    return json_response('success', {'reward': problem.reward}, 'Задание выполнено')

@app.route('/api/problems/complete_with_photos', methods=['POST'])
@login_required
def complete_problem_with_photos():
    """Завершить задание с фотоотчетом"""
    try:
        problem_id = request.form.get('problem_id')
        if not problem_id:
            return json_response('error', {}, 'ID проблемы не указан', 400)
            
        problem = Problem.query.get_or_404(int(problem_id))
        
        if problem.assigned_to != current_user.id:
            return json_response('error', {}, 'Вы не выполняете это задание', 403)
        
        # Сохраняем фото "было" и "стало" с использованием утилиты
        before_path = save_uploaded_file(request.files.get('before_photo'), prefix='before')
        after_path = save_uploaded_file(request.files.get('after_photo'), prefix='after')
        
        # Создаем отчет о выполнении
        completion = TaskCompletion(
            problem_id=problem.id,
            user_id=current_user.id,
            before_photo=before_path,
            after_photo=after_path,
            description=request.form.get('description', '')
        )
        
        # Обновляем статус проблемы
        problem.status = ProblemStatus.COMPLETED
        problem.completed_at = datetime.utcnow()
        
        # Начисляем награду
        current_user.points += problem.reward
        current_user.total_completed += 1
        current_user.experience += 50
        
        # Проверяем достижения
        current_user.check_achievements()
        
        db.session.add(completion)
        db.session.commit()
        
        return json_response('success', {'reward': problem.reward}, 'Задание выполнено с фотоотчетом')
        
    except Exception as e:
        app.logger.error(f"Error completing problem with photos: {e}")
        return json_response('error', {}, f'Ошибка: {str(e)}', 500)

@app.route('/api/problems/<int:problem_id>/vote', methods=['POST'])
@login_required
def vote_problem(problem_id: int):
    """Проголосовать за проблему"""
    data = request.get_json()
    if not data:
        return json_response('error', {}, 'Нет данных', 400)
        
    vote_type = data.get('type')  # 'like' или 'dislike'
    
    if vote_type not in ['like', 'dislike']:
        return json_response('error', {}, 'Неверный тип голоса', 400)
    
    # Проверяем, не голосовал ли уже пользователь
    existing_vote = Vote.query.filter_by(
        problem_id=problem_id,
        user_id=current_user.id
    ).first()
    
    problem = Problem.query.get_or_404(problem_id)
    
    if existing_vote:
        # Если повторный голос того же типа - удаляем
        if existing_vote.vote_type == vote_type:
            db.session.delete(existing_vote)
            if vote_type == 'like':
                problem.likes -= 1
            else:
                problem.dislikes -= 1
        else:
            # Если меняем голос - обновляем
            if existing_vote.vote_type == 'like':
                problem.likes -= 1
                problem.dislikes += 1
            else:
                problem.dislikes -= 1
                problem.likes += 1
            existing_vote.vote_type = vote_type
    else:
        # Новый голос
        vote = Vote(
            problem_id=problem_id,
            user_id=current_user.id,
            vote_type=vote_type
        )
        db.session.add(vote)
        
        if vote_type == 'like':
            problem.likes += 1
        else:
            problem.dislikes += 1
    
    db.session.commit()
    
    return json_response('success', {
        'likes': problem.likes,
        'dislikes': problem.dislikes
    }, 'Голос учтен')

@app.route('/api/problems/<int:problem_id>/vote_status')
@login_required
def get_vote_status(problem_id: int):
    """Получить статус голосования пользователя"""
    vote = Vote.query.filter_by(
        problem_id=problem_id,
        user_id=current_user.id
    ).first()
    
    problem = Problem.query.get_or_404(problem_id)
    
    return json_response('success', {
        'user_vote': vote.vote_type if vote else None,
        'likes': problem.likes,
        'dislikes': problem.dislikes
    })

@app.route('/api/problems/<int:problem_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_problem(problem_id: int):
    """Удаление проблемы (Админ)"""
    problem = Problem.query.get_or_404(problem_id)
    
    # Удаляем связанные жалобы, если есть
    Complaint.query.filter_by(problem_id=problem.id).delete()
    Comment.query.filter_by(problem_id=problem.id).delete()
    Vote.query.filter_by(problem_id=problem.id).delete()
    TaskCompletion.query.filter_by(problem_id=problem.id).delete()
    
    db.session.delete(problem)
    db.session.commit()
    return json_response('success', {}, 'Проблема удалена')

@app.route('/api/comments/add', methods=['POST'])
@login_required
def add_comment():
    """Добавить комментарий"""
    data = request.get_json()
    if not data or not data.get('text') or not data.get('problem_id'):
        return json_response('error', {}, 'Неверные данные', 400)
    
    comment = Comment(
        problem_id=data.get('problem_id'),
        user_id=current_user.id,
        text=data.get('text')
    )
    db.session.add(comment)
    db.session.commit()
    return json_response('success', {}, 'Комментарий добавлен')

@app.route('/api/comments/<int:problem_id>', methods=['GET'])
@login_required
def get_comments(problem_id: int):
    """Получить комментарии к проблеме"""
    comments = Comment.query.filter_by(problem_id=problem_id).order_by(Comment.created_at.asc()).all()
    comments_data = [{
        'id': c.id,
        'user': c.user.username,
        'text': c.text,
        'created_at': c.created_at.isoformat(),
        'avatar': c.user.avatar
    } for c in comments]
    
    return json_response('success', {'comments': comments_data})

@app.route('/api/complaints/add', methods=['POST'])
@login_required
def add_complaint():
    """Подать жалобу"""
    data = request.get_json()
    if not data or not data.get('reason') or not data.get('problem_id'):
        return json_response('error', {}, 'Неверные данные', 400)
    
    complaint = Complaint(
        problem_id=data.get('problem_id'),
        user_id=current_user.id,
        reason=data.get('reason'),
        description=data.get('description', ''),
        status=ComplaintStatus.PENDING
    )
    db.session.add(complaint)
    db.session.commit()
    return json_response('success', {}, 'Жалоба отправлена')

@app.route('/api/complaints/<int:complaint_id>/resolve', methods=['POST'])
@login_required
@admin_required
def resolve_complaint(complaint_id: int):
    """Разрешить жалобу (Админ)"""
    data = request.get_json()
    action = data.get('action') if data else None  # 'delete_content', 'reject_complaint'
    delete_prob = data.get('delete_problem', False) if data else False
    
    complaint = Complaint.query.get_or_404(complaint_id)
    
    if delete_prob or action == 'delete_content':
        if complaint.problem:
            db.session.delete(complaint.problem)
            
    complaint.status = ComplaintStatus.RESOLVED
    db.session.commit()
    
    return json_response('success', {}, 'Жалоба обработана')

@app.route('/api/user/<int:user_id>/toggle_admin', methods=['POST'])
@login_required
@admin_required
def toggle_admin(user_id: int):
    """Сделать пользователя админом или разжаловать"""
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        return json_response('error', {}, 'Нельзя изменить свои права', 400)
        
    user.is_admin = not user.is_admin
    db.session.commit()
    return json_response('success', {'is_admin': user.is_admin}, 
                        f'Права {"выданы" if user.is_admin else "сняты"}')

@app.route('/api/user/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id: int):
    """Удалить пользователя (Админ)"""
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        return json_response('error', {}, 'Нельзя удалить себя', 400)
    
    # Удаляем связанные данные
    Problem.query.filter_by(user_id=user.id).delete()
    Complaint.query.filter_by(user_id=user.id).delete()
    Comment.query.filter_by(user_id=user.id).delete()
    Vote.query.filter_by(user_id=user.id).delete()
    TaskCompletion.query.filter_by(user_id=user.id).delete()
    Order.query.filter_by(user_id=user.id).delete()
    
    db.session.delete(user)
    db.session.commit()
    
    return json_response('success', {}, 'Пользователь удален')

@app.route('/api/user/<int:user_id>/reset_password', methods=['POST'])
@login_required
@admin_required
def reset_user_password(user_id: int):
    """Сбросить пароль пользователя (Админ)"""
    user = User.query.get_or_404(user_id)
    new_password = secrets.token_urlsafe(8)[:10]  # Генерация случайного пароля
    
    user.set_password(new_password)
    db.session.commit()
    
    return json_response('success', {'password': new_password}, 'Пароль сброшен')

@app.route('/api/user/<int:user_id>/edit', methods=['POST'])
@login_required
@admin_required
def edit_user(user_id: int):
    """Редактировать пользователя (Админ)"""
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    if not data:
        return json_response('error', {}, 'Нет данных', 400)
    
    if 'points' in data:
        user.points = int(data['points'])
    if 'is_worker' in data:
        user.is_worker = bool(data['is_worker'])
    if 'city' in data:
        user.city = str(data['city'])[:100]
    
    db.session.commit()
    return json_response('success', {}, 'Данные обновлены')

@app.route('/api/problems/<int:problem_id>/edit', methods=['POST'])
@login_required
@admin_required
def edit_problem(problem_id: int):
    """Редактировать проблему (Админ)"""
    problem = Problem.query.get_or_404(problem_id)
    data = request.get_json()
    
    if not data:
        return json_response('error', {}, 'Нет данных', 400)
    
    if 'title' in data:
        problem.title = str(data['title'])[:200]
    if 'description' in data:
        problem.description = str(data['description'])
    if 'severity' in data:
        problem.severity = int(data['severity'])
    if 'reward' in data:
        problem.reward = int(data['reward'])
    if 'status' in data and data['status'] in ProblemStatus.ALL:
        problem.status = data['status']
    
    db.session.commit()
    return json_response('success', {}, 'Проблема обновлена')

@app.route('/api/tasks/create', methods=['POST'])
@login_required
@admin_required
def create_task():
    """Создать задачу вручную (Админ)"""
    data = request.get_json()
    if not data or not data.get('title'):
        return json_response('error', {}, 'Неверные данные', 400)
    
    lat, lng = get_coordinates_from_request(request)
    
    task = Problem(
        lat=lat,
        lng=lng,
        title=data['title'],
        description=data.get('description', ''),
        category=data.get('category', ProblemCategory.OTHER),
        severity=data.get('severity', ProblemSeverity.MEDIUM),
        reward=data.get('reward', ConfigDefaults.POINTS_FOR_POINT),
        user_id=current_user.id,
        status=ProblemStatus.REPORTED
    )
    
    db.session.add(task)
    db.session.commit()
    
    return json_response('success', {'id': task.id}, 'Задача создана')

@app.route('/api/user/update_balance', methods=['POST'])
@login_required
def update_balance():
    """Изменить баланс (покупка в магазине и т.д.)"""
    data = request.get_json()
    if not data:
        return json_response('error', {}, 'Нет данных', 400)
        
    amount = int(data.get('amount', 0))
    current_user.points += amount
    db.session.commit()
    return json_response('success', {'new_balance': current_user.points}, 'Баланс обновлен')

@app.route('/api/orders', methods=['GET'])
@login_required
@admin_required
def get_orders():
    """Получить заказы (только для админа)"""
    orders = Order.query.order_by(Order.created_at.desc()).all()
    orders_data = []
    
    for order in orders:
        orders_data.append({
            'id': order.id,
            'user': order.user.username if order.user else 'Неизвестно',
            'item': order.item_name,
            'price': order.price,
            'quantity': order.quantity,
            'address': order.address or '',
            'phone': order.phone or '',
            'size': order.size or '',
            'status': order.status,
            'created_at': order.created_at.strftime('%d.%m.%Y %H:%M') if order.created_at else '',
            'total': order.price * order.quantity
        })
    
    return jsonify(orders_data)
    
@app.route('/api/orders/create', methods=['POST'])
@login_required
def create_order():
    """Создать заказ"""
    try:
        data = request.get_json()
        if not data:
            return json_response('error', {}, 'Нет данных', 400)
        
        # Проверяем баланс
        item_price = int(data.get('price', 0))
        if current_user.points < item_price:
            return json_response('error', {}, 'Недостаточно средств', 400)
        
        # Создаем заказ
        order = Order(
            user_id=current_user.id,
            item_id=data.get('item_id'),
            item_name=data.get('item_name'),
            price=item_price,
            quantity=data.get('quantity', 1),
            address=data.get('address'),
            phone=data.get('phone'),
            size=data.get('size', ''),
            comment=data.get('comment', ''),
            status=OrderStatus.PENDING
        )
        
        # Списание баллов
        current_user.points -= item_price
        
        # Проверяем достижения для заказа
        orders_count = Order.query.filter_by(user_id=current_user.id).count()
        if orders_count == 0:  # Если это первый заказ (перед добавлением нового заказа)
            current_user.add_badge('Первый заказ', 'fa-shopping-bag')
        
        # Проверяем другие достижения
        current_user.check_achievements()
        
        db.session.add(order)
        db.session.commit()
        
        return json_response('success', {'order_id': order.id}, 'Заказ создан')
        
    except Exception as e:
        app.logger.error(f"Error creating order: {e}")
        return json_response('error', {}, f'Ошибка: {str(e)}', 500)

@app.route('/api/orders/<int:order_id>/update_status', methods=['POST'])
@login_required
@admin_required
def update_order_status(order_id: int):
    """Обновить статус заказа (админ)"""
    order = Order.query.get_or_404(order_id)
    data = request.get_json()
    
    if not data or 'status' not in data:
        return json_response('error', {}, 'Статус не указан', 400)
    
    new_status = data['status']
    if new_status not in OrderStatus.NAMES:
        return json_response('error', {}, 'Неверный статус', 400)
    
    order.status = new_status
    order.updated_at = datetime.utcnow()
    
    db.session.commit()
    return json_response('success', {}, f'Статус обновлен на {OrderStatus.NAMES.get(new_status, new_status)}')

@app.route('/api/daily_challenge')
@login_required
def get_daily_challenge():
    """Получить текущий ежедневный челлендж"""
    today = datetime.utcnow().date()
    today_problems = Problem.query.filter(
        Problem.user_id == current_user.id,
        db.func.date(Problem.created_at) == today
    ).count()
    
    challenges = [
        {'id': 1, 'name': 'Первая проблема', 'target': 1, 'reward': 10},
        {'id': 2, 'name': 'Три проблемы за день', 'target': 3, 'reward': 30},
        {'id': 3, 'name': 'Помочь с 5 заданиями', 'target': 5, 'reward': 50},
    ]
    
    completed = []
    for challenge in challenges:
        if today_problems >= challenge['target']:
            completed.append(challenge['id'])
    
    return json_response('success', {
        'challenges': challenges,
        'completed': completed,
        'today_problems': today_problems
    })

# ==========================================
# ИНТЕГРАЦИЯ ДАТЧИКОВ (OpenWeatherMap)
# ==========================================

@app.route('/api/sensors', methods=['GET'])
def get_sensors():
    """
    Получает данные о погоде и загрязнении воздуха для указанных координат.
    Если API ключ невалиден или лимит исчерпан, возвращает мок-данные.
    """
    # Получаем координаты из GET параметров или берем дефолтные
    lat, lng = get_coordinates_from_request(request)
    
    api_key = app.config.get('OPENWEATHER_API_KEY')
    sensors = []
    
    try:
        # Проверяем, задан ли ключ (не заглушка)
        if api_key and api_key != 'ВАШ_API_KEY_ЗДЕСЬ':
            # 1. Запрос погоды
            weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lng}&appid={api_key}&units=metric"
            w_res = requests.get(weather_url, timeout=3)
            
            # 2. Запрос загрязнения (AQI)
            air_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lng}&appid={api_key}"
            a_res = requests.get(air_url, timeout=3)
            
            if w_res.status_code == 200:
                w_data = w_res.json()
                # Создаем виртуальный датчик температуры
                sensors.append({
                    'sensor_id': 'TEMP-MAIN',
                    'sensor_type': 'temperature',
                    'value': w_data['main']['temp'],
                    'timestamp': datetime.utcnow().isoformat(),
                    'lat': lat + 0.002, # Слегка смещаем для отображения на карте
                    'lng': lng + 0.002
                })
                # Виртуальный датчик влажности
                sensors.append({
                    'sensor_id': 'HUM-MAIN',
                    'sensor_type': 'soil_moisture', # Используем как влажность почвы/воздуха
                    'value': w_data['main']['humidity'],
                    'timestamp': datetime.utcnow().isoformat(),
                    'lat': lat - 0.002,
                    'lng': lng + 0.001
                })
                
            if a_res.status_code == 200:
                a_data = a_res.json()
                aqi = a_data['list'][0]['main']['aqi'] # 1 (хорошо) - 5 (плохо)
                # Переводим в "индекс чистоты" (100 - отлично, 0 - ужасно)
                purity_index = 100 - ((aqi - 1) * 25)
                sensors.append({
                    'sensor_id': 'AIR-QA',
                    'sensor_type': 'soil_moisture', # Реюзинг типа для графика
                    'value': purity_index,
                    'timestamp': datetime.utcnow().isoformat(),
                    'lat': lat + 0.001,
                    'lng': lng - 0.003
                })
                
        else:
            raise Exception("API Key not configured")
            
    except Exception as e:
        app.logger.warning(f"Sensor API Error (using mocks): {e}")
        # MOCK DATA (Генерация случайных значений, если API не работает)
        for i in range(1, 6):
            val = random.uniform(15, 30) if i % 2 == 0 else random.uniform(40, 80)
            stype = 'temperature' if i % 2 == 0 else 'soil_moisture'
            sensors.append({
                'sensor_id': f'SENS-{i:03d}',
                'sensor_type': stype,
                'value': round(val, 1),
                'timestamp': datetime.utcnow().isoformat(),
                'lat': lat + random.uniform(-0.02, 0.02),
                'lng': lng + random.uniform(-0.02, 0.02)
            })
    
    return jsonify(sensors)
    
# ==========================================
# ИНИЦИАЛИЗАЦИЯ
# ==========================================

def init_db():
    """Создание таблиц и администратора при первом запуске"""
    with app.app_context():
        # Создаем таблицы
        db.create_all()
        
        # Создаем админа, если нет
        if not User.query.filter_by(username='admin').first():
            app.logger.info("Создаем учетную запись администратора (admin / admin123)...")
            admin = User(
                username='admin', 
                email='admin@fm.ru', 
                is_admin=True, 
                points=1000,
                city=ConfigDefaults.CITY_NAME
            )
            admin.set_password('admin123')
            admin.referral_code = secrets.token_urlsafe(8)[:10]
            db.session.add(admin)
            
        # Создаем тестового пользователя
        if not User.query.filter_by(username='user1').first():
            app.logger.info("Создаем тестового пользователя (user1 / user123)...")
            user = User(
                username='user1', 
                email='user@fm.ru', 
                points=100,
                city=ConfigDefaults.CITY_NAME
            )
            user.set_password('user123')
            user.referral_code = secrets.token_urlsafe(8)[:10]
            db.session.add(user)
            
        # Добавляем тестовую проблему
        if Problem.query.count() == 0:
            app.logger.info("Добавляем тестовые данные...")
            p1 = Problem(
                lat=ConfigDefaults.CITY_CENTER[0] + 0.002, 
                lng=ConfigDefaults.CITY_CENTER[1] + 0.002,
                title='Тестовая проблема: Мусор',
                description='Пример описания проблемы.',
                category=ProblemCategory.POLLUTION,
                user_id=1,
                status=ProblemStatus.REPORTED
            )
            db.session.add(p1)
            
        db.session.commit()
        app.logger.info("База данных готова. Все таблицы созданы.")

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
