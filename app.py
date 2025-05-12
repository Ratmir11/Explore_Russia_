import time

from flask import Flask, request, jsonify, render_template, session, redirect, url_for
import os
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import bcrypt
from databaser import Databaser
from config import APP_SECRET_KEY
from geopy.distance import geodesic

app = Flask(__name__)
app.secret_key = APP_SECRET_KEY  # Нужен для работы сессий

db = Databaser('travel.db')


def hash_password(password):
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed


# Проверка пароля
def verify_password(plain_password: str, hashed_password: str) -> bool:
    hashed_password_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password_bytes)


app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Создайте папку для загрузки файлов, если она не существует
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/')
def home():
    if 'user_id' in session:  # Проверяем, есть ли пользователь в сессии
        users_list = db.get_all_users_list()
        return render_template('index.html', username=session['username'], users=users_list)
    return redirect(url_for('login'))  # Если нет, перенаправляем на страницу входа



@app.route('/register', methods=['GET', 'POST'])
def register():
    country_id = 1
    city_list = db.get_all_cities_from_country_id(country_id)

    if request.method == 'POST':
        nickname = request.form['nickname'].strip()
        city_name = request.form['city'].strip()
        password = request.form['password'].strip()

        # Проверяем, существует ли пользователь
        existing_user = db.get_user_id_from_nickname(nickname)
        if existing_user is not None:
            return render_template('register.html', cities=city_list,
                                   error="Пользователь с таким именем уже существует")

        if city_name not in [i[1] for i in city_list]:
            return render_template('register.html', cities=city_list,
                                   error="Города с таким названием нет в списке")

        db.add_user(nickname, city_name, password)
        user_id = db.get_user_id_from_nickname(nickname)

        # Сохраняем данные в сессии
        session['user_id'] = user_id
        session['username'] = nickname
        session['city_name'] = db.get_city_name_from_user_id(user_id=user_id)
        session['registered'] = True  # Добавляем флаг регистрации

        return redirect(url_for('home'))  # Перенаправляем на главную страницу

    return render_template('register.html', cities=city_list)  # Передаем города в шаблон


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nickname = request.form['nickname']
        password = request.form['password']

        # Проверяем, существует ли пользователь с таким ником
        user_id = db.get_user_id_from_nickname(nickname)
        if user_id is None:
            return render_template('login.html', error="Пользователь не найден")

        # Получаем хэш пароля из базы данных
        correct_password = db.get_user_password(user_id)  # Функция для получения пароля по user_id

        # Проверяем правильность пароля
        if not verify_password(password, correct_password):
            return render_template('login.html', error="Неверный пароль")

        # Если все верно, сохраняем данные в сессии
        session['user_id'] = user_id
        session['city_name'] = db.get_city_name_from_user_id(user_id=user_id)
        session['username'] = nickname

        return redirect(url_for('home'))  # Перенаправляем на главную страницу

    return render_template('login.html')  # Если GET запрос, показываем форму для входа


@app.route('/profile')
def profile():
    country_id = 1
    city_list = db.get_all_cities_from_country_id(country_id)
    # Проверяем, авторизован ли пользователь
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Если нет, перенаправляем на страницу входа

    user_id = session['user_id']
    username = session['username']
    city_name = session['city_name']
    # Получаем город и рейтинг пользователя
    rating = db.get_user_rating(user_id)

    return render_template('profile.html', username=username, user_city=city_name, user_rating=rating, city_list=city_list)


@app.route('/logout')
def logout():
    session.clear()  # Очищаем сессию, разлогиниваем пользователя
    return redirect(url_for('home'))  # Перенаправляем на главную страницу


@app.route('/get_attraction', methods=['POST'])
def get_attraction():
    if 'user_id' not in session:
        return {"success": False, "error": "Вы не авторизованы"}, 401

    user_id = session['user_id']
    t_t_t_attractions = db.get_time_to_take_attractions_from_user_id(user_id=user_id)

    # Если t_t_t_attractions = 0 (или None), то приравниваем его к началу эпохи
    last_taken_time = t_t_t_attractions if t_t_t_attractions else 0

    # Проверяем, прошло ли 24 часа
    if time.time() - last_taken_time > timedelta(hours=24).total_seconds() or 1:
        try:
            # Получаем случайную достопримечательность для пользователя
            attraction_id = db.get_random_attractions_from_user(user_id)
            if attraction_id:
                # Устанавливаем достопримечательность пользователю
                time_take_attraction = time.time()
                db.give_user_attractions(user_id, attraction_id, time_take_attraction, 1)

                return {"success": True, "attraction_id": attraction_id}
            else:
                return {"success": False, "error": "Нет доступных достопримечательностей"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    else:
        return jsonify(
            {"success": False, "error": "Или прошло меньше 24 часов с последнего получения достопримечательности или"
                                        " у вас уже есть достопримечательность для посещения"})


@app.route('/game')
def game():
    # Получаем user_id из сессии
    user_id = session.get('user_id')

    if not user_id:
        return render_template('game.html', error_message="Вы не авторизованы")

    # Проверяем, есть ли достопримечательность в attractions_now
    attraction_id = db.get_attractions_now_from_user(user_id)

    if attraction_id:
        # Получаем URL картинки
        image_url = db.get_url_image_from_attractions_id(attraction_id)

        # Получаем информацию о достопримечательности
        attraction_info = db.get_all_info_about_attractions(attraction_id)

        # Извлекаем нужные поля из информации о достопримечательности
        name = attraction_info[0][1]  # Название
        description = attraction_info[0][2] if attraction_info[0][2] else "Описание отсутствует"
        address = attraction_info[0][5]  # Адрес
        latitude = attraction_info[0][6]  # Широта
        longitude = attraction_info[0][7]  # Долгота

        # Передаем данные в шаблон
        return render_template('game.html',
                               name=name,
                               image_url=image_url,
                               description=description,
                               address=address,
                               latitude=latitude,
                               longitude=longitude)
    else:
        # Если достопримечательности нет, показываем сообщение
        return render_template('game.html', error_message="Достопримечательность для посещения отсутствует")


@app.route('/check_location', methods=['POST'])
def check_location():
    if 'user_id' not in session:
        return {"success": False, "error": "Вы не авторизованы"}, 401

    data = request.get_json()
    latitude = data.get('latitude')
    longitude = data.get('longitude')

    user_id = session.get('user_id')
    attraction_id = db.get_attractions_now_from_user(user_id=user_id)
    if attraction_id is None:
        return {"success": False, "error": "У вас нет достопримечательности для посещения"}

    correct_latitude, correct_longitude = db.get_coords_from_attractions_id(attraction_id)

    if correct_latitude is None or correct_longitude is None:
        return {"success": False, "error": "Координаты достопримечательности не найдены"}

    # Преобразование координат в float
    correct_latitude, correct_longitude = float(correct_latitude), float(correct_longitude)

    # Логика для проверки, находится ли пользователь в пределах 100 метров
    # if abs(latitude - correct_latitude) < 0.01 and abs(longitude - correct_longitude) < 0.01:
    if abs(latitude - correct_latitude) < 1000000 and abs(longitude - correct_longitude) < 1000000:
        # Удаление текущей достопримечательности
        db.remove_current_attraction(user_id)

        # Добавление в dedicated_attractions
        db.add_to_dedicated_attractions(user_id, attraction_id)

        # Начисление рейтинга
        selection_type = db.get_selection_type_from_user(user_id)
        if selection_type == '1':
            points = 30
        elif selection_type == '2':
            points = 15
        else:
            points = 0

        db.update_user_rating(user_id, points)

        return {"success": True}
    else:
        return {"success": False, "error": "Вы не в правильном месте"}


@app.route('/upload_photo', methods=['POST'])
def upload_photo():
    if 'user_id' not in session:
        return jsonify({"success": False, "error": "Вы не авторизованы"}), 401

    if 'photo' not in request.files:
        return jsonify({"success": False, "error": "Файл не найден"}), 400

    file = request.files['photo']

    if file.filename == '':
        return jsonify({"success": False, "error": "Файл не выбран"}), 400

    if file and allowed_file(file.filename):
        # Сохраняем файл на сервере
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Сохраняем путь к файлу для модерации
        db.save_photo_for_moderation(filepath, filename, session['user_id'])

        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "Недопустимый тип файла"}), 400


@app.route('/attractions')
def attractions():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('attractions.html')


@app.route('/get_attractions')
def get_attractions():
    # Проверяем, авторизован ли пользователь
    if 'user_id' not in session:
        return jsonify({"success": False, "error": "Вы не авторизованы"}), 401

    user_id = session['user_id']

    # Получаем время последнего получения достопримечательностей
    t_t_t_attractions = db.get_time_to_take_attractions_from_user_id(user_id=user_id)
    last_taken_time = t_t_t_attractions if t_t_t_attractions else 0
    can_take = time.time() - last_taken_time > timedelta(hours=24).total_seconds()

    # Получаем city_id для пользователя
    city_id = db.get_city_id_from_user_id(user_id)

    # Получаем параметры страницы и фильтров
    page = int(request.args.get('page', 1))
    limit = 10  # Количество достопримечательностей на страницу
    offset = (page - 1) * limit

    user_lat = request.args.get('user_lat', type=float)
    user_lon = request.args.get('user_lon', type=float)

    # Проверка на наличие координат пользователя
    if user_lat is None or user_lon is None:
        return jsonify({"success": False, "error": "Не указаны координаты пользователя"}), 400

    min_distance = request.args.get('min_distance', type=float, default=0)
    max_distance = request.args.get('max_distance', type=float, default=float('inf'))

    # Проверка на корректность значений дистанции
    if min_distance > max_distance:
        return jsonify({"success": False, "error": "Минимальная дистанция не может быть больше максимальной"}), 400

    attractions = db.get_attractions_by_city_id(city_id)

    # Фильтрация достопримечательностей по расстоянию
    filtered_attractions = []
    for attraction in attractions:
        attraction_coords = (attraction[4], attraction[5])
        user_coords = (user_lat, user_lon)
        distance = geodesic(user_coords, attraction_coords).kilometers
        if min_distance <= distance <= max_distance:
            filtered_attractions.append(attraction)

    # Пагинация: если на текущей странице нет данных, то отправляем пустой список
    total_attractions = len(filtered_attractions)
    attractions_on_page = filtered_attractions[offset:offset + limit]

    if not attractions_on_page and page > 1:
        return jsonify({"success": False, "error": "По вашему запросу ничего не найдено"}), 404

    print(*attractions_on_page, sep='\n')

    # Формируем список достопримечательностей для отправки на фронт
    attractions_list = []
    for attraction in attractions_on_page:
        attraction_id = attraction[0]
        image_url = db.get_url_image_from_attractions_id(attraction_id)
        attractions_list.append({
            "id": attraction_id,
            "name": attraction[1],
            "image_url": image_url,
            "description": attraction[2],
            "address": attraction[3],
            "latitude": attraction[4],
            "longitude": attraction[5],
            "can_take": can_take
        })

    # Проверяем, если на странице больше нет данных, отправляем сообщение об окончании
    if len(attractions_on_page) < limit:
        return jsonify({"attractions": attractions_list, "end_of_results": True})

    return jsonify({"attractions": attractions_list})


@app.route('/take_attraction', methods=['POST'])
def take_attraction():
    if 'user_id' not in session:
        return jsonify({"success": False, "error": "Вы не авторизованы"}), 401

    data = request.get_json()
    attraction_id = data.get('attraction_id')
    user_id = session['user_id']
    t_t_t_attractions = db.get_time_to_take_attractions_from_user_id(user_id=user_id)
    last_taken_time = t_t_t_attractions if t_t_t_attractions else 0

    if time.time() - last_taken_time > timedelta(minutes=1).total_seconds():
        time_take_attraction = time.time()
        db.give_user_attractions(user_id, attraction_id, time_take_attraction, 2)
        return jsonify({"success": True})
    else:
        return jsonify(
            {"success": False, "error": "Или прошло меньше 24 часов с последнего получения достопримечательности или"
                                        " у вас уже есть достопримечательность для посещения"})



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
