from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import requests
import random

# Импорт конфигурации и моделей
from config import Config
from models import db, User, Problem, Complaint

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
def load_user(user_id):
    return User.query.get(int(user_id))

@app.context_processor
def inject_global_vars():
    return {
        'current_user': current_user,
        'now': datetime.utcnow()
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
def admin_panel():
    if not current_user.is_admin:
        flash('Доступ запрещен. Требуются права администратора.', 'error')
        return redirect(url_for('index'))
    
    users = User.query.all()
    problems = Problem.query.all()
    complaints = Complaint.query.filter_by(status='pending').all()
    tasks = Problem.query.filter(Problem.status != 'completed').all()
    
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
def admin_profile_view():
    """Отдельная страница управления для админа (из admin_profile.html)"""
    if not current_user.is_admin:
        return redirect(url_for('index'))
        
    users = User.query.all()
    problems = Problem.query.all()
    complaints = Complaint.query.filter_by(status='pending').all()
    
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
    my_completed = Problem.query.filter_by(assigned_to=current_user.id, status='completed').order_by(Problem.completed_at.desc()).all()
    
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
    user_tasks = Problem.query.filter_by(assigned_to=current_user.id, status='in_progress').all()
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
    available_tasks = Problem.query.filter_by(status='reported', assigned_to=None).all()
    # Мои текущие задания
    my_tasks = Problem.query.filter_by(assigned_to=current_user.id, status='in_progress').all()
    
    return render_template('tasks.html', tasks=available_tasks, my_tasks=my_tasks)

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
    active_points = len([p for p in problems if p.status != 'completed'])
    completed_points = len([p for p in problems if p.status == 'completed'])
    
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
    city_name = app.config.get('CITY_NAME', 'Киселевск')

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
    problems = Problem.query.filter(Problem.status != 'completed').all()
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
            'photo': p.photo # URL фото
        })
    return jsonify(result)

@app.route('/api/problems/add', methods=['POST'])
@login_required
def add_problem():
    """Добавление проблемы с фото (FormData)"""
    try:
        title = request.form.get('title')
        lat = float(request.form.get('lat'))
        lng = float(request.form.get('lng'))
        description = request.form.get('description', '')
        category = request.form.get('category', 'other')
        severity = int(request.form.get('severity', 3))
        
        # Обработка файла
        photo_path = None
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename != '':
                filename = secure_filename(f"prob_{datetime.now().timestamp()}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                photo_path = f"/static/uploads/{filename}"

        problem = Problem(
            lat=lat, lng=lng,
            title=title,
            description=description,
            category=category,
            severity=severity,
            photo=photo_path,
            user_id=current_user.id,
            reward=app.config.get('POINTS_FOR_POINT', 15)
        )
        
        # Начисляем опыт и баллы создателю
        current_user.points += app.config.get('POINTS_FOR_POINT', 15)
        current_user.total_reports += 1
        current_user.experience += 30
        
        db.session.add(problem)
        db.session.commit()
        
        return jsonify({'status': 'success', 'id': problem.id})
    except Exception as e:
        print(f"Error adding problem: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/problems/<int:problem_id>/take', methods=['POST'])
@login_required
def take_problem(problem_id):
    """Взять задание в работу"""
    problem = Problem.query.get_or_404(problem_id)
    
    if problem.assigned_to:
        return jsonify({'status': 'error', 'message': 'Задание уже занято'})
    
    problem.assigned_to = current_user.id
    problem.status = 'in_progress'
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/api/problems/<int:problem_id>/complete', methods=['POST'])
@login_required
def complete_problem(problem_id):
    """Отметить задание выполненным"""
    problem = Problem.query.get_or_404(problem_id)
    
    # Проверка прав (либо автор, либо исполнитель, либо админ)
    if not (current_user.id == problem.assigned_to or current_user.is_admin):
        # В некоторых механиках автор тоже может закрыть
        pass 

    if problem.status == 'completed':
        return jsonify({'status': 'error', 'message': 'Уже выполнено'})
        
    problem.status = 'completed'
    problem.completed_at = datetime.utcnow()
    
    # Начисляем награду тому, кто выполнил (или текущему юзеру, если он закрыл)
    current_user.points += problem.reward
    current_user.total_completed += 1
    current_user.experience += 50
    
    db.session.commit()
    return jsonify({'status': 'success', 'reward': problem.reward})

@app.route('/api/problems/<int:problem_id>/delete', methods=['POST'])
@login_required
def delete_problem(problem_id):
    """Удаление проблемы (Админ)"""
    if not current_user.is_admin:
        return jsonify({'status': 'error', 'message': 'Нет прав'}), 403
        
    problem = Problem.query.get_or_404(problem_id)
    
    # Удаляем связанные жалобы, если есть (каскадное удаление лучше настроить в БД, но сделаем вручную)
    Complaint.query.filter_by(problem_id=problem.id).delete()
    
    db.session.delete(problem)
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/api/complaints/add', methods=['POST'])
@login_required
def add_complaint():
    """Подать жалобу"""
    data = request.json
    complaint = Complaint(
        problem_id=data.get('problem_id'),
        user_id=current_user.id,
        reason=data.get('reason'),
        description=data.get('description')
    )
    db.session.add(complaint)
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/api/complaints/<int:complaint_id>/resolve', methods=['POST'])
@login_required
def resolve_complaint(complaint_id):
    """Разрешить жалобу (Админ)"""
    if not current_user.is_admin:
        return jsonify({'status': 'error', 'message': 'Нет прав'}), 403
        
    data = request.json
    action = data.get('action') # 'delete_content', 'reject_complaint'
    delete_prob = data.get('delete_problem', False)
    
    complaint = Complaint.query.get_or_404(complaint_id)
    
    if delete_prob or action == 'delete_content':
        if complaint.problem:
            db.session.delete(complaint.problem)
            
    complaint.status = 'resolved'
    db.session.commit()
    
    return jsonify({'status': 'success'})

@app.route('/api/user/<int:user_id>/toggle_admin', methods=['POST'])
@login_required
def toggle_admin(user_id):
    """Сделать пользователя админом или разжаловать"""
    if not current_user.is_admin:
        return jsonify({'status': 'error', 'message': 'Нет прав'}), 403
        
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        return jsonify({'status': 'error', 'message': 'Нельзя изменить свои права'}), 400
        
    user.is_admin = not user.is_admin
    db.session.commit()
    return jsonify({'status': 'success', 'is_admin': user.is_admin})

@app.route('/api/user/update_balance', methods=['POST'])
@login_required
def update_balance():
    """Изменить баланс (покупка в магазине и т.д.)"""
    data = request.json
    amount = data.get('amount', 0)
    current_user.points += amount
    db.session.commit()
    return jsonify({'status': 'success'})

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
    lat = request.args.get('lat', type=float) or app.config['CITY_CENTER'][0]
    lng = request.args.get('lng', type=float) or app.config['CITY_CENTER'][1]
    
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
        print(f"Sensor API Error (using mocks): {e}")
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
            print("Создаем учетную запись администратора (admin / admin123)...")
            admin = User(
                username='admin', 
                email='admin@fm.ru', 
                is_admin=True, 
                points=1000,
                city='Киселевск'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            
        # Создаем тестового пользователя
        if not User.query.filter_by(username='user1').first():
            print("Создаем тестового пользователя (user1 / user123)...")
            user = User(
                username='user1', 
                email='user@fm.ru', 
                points=100,
                city='Киселевск'
            )
            user.set_password('user123')
            db.session.add(user)
            
        # Добавляем тестовую проблему
        if Problem.query.count() == 0:
            print("Добавляем тестовые данные...")
            p1 = Problem(
                lat=app.config['CITY_CENTER'][0] + 0.002, 
                lng=app.config['CITY_CENTER'][1] + 0.002,
                title='Тестовая проблема: Мусор',
                description='Пример описания проблемы.',
                category='pollution',
                user_id=1
            )
            db.session.add(p1)
            
        db.session.commit()
        print("База данных готова.")

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)