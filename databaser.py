import os
import sqlite3
from datetime import datetime
import random
import bcrypt

def hash_password(password):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt)

class Databaser:
    def __init__(self, db_path):
        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row

    def close_connection(self):
        if self.connection:
            self.connection.close()

    def get_all_countries(self):
        try:
            with self.connection:
                cursor = self.connection.execute("SELECT name FROM country")
                return [row["name"] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Ошибка при получении списка стран: {e}")
            return []

    def get_all_cities_from_country_id(self, country_id):
        try:
            with self.connection:
                cursor = self.connection.execute(
                    "SELECT name FROM city WHERE country_id = ?",
                    (country_id,)
                )
                return [(i, row[0]) for i, row in enumerate(cursor.fetchall())]
        except Exception as e:
            print(f"Ошибка при получении списка городов: {e}")
            return []

    def get_city_id_from_city_name(self, city_name):
        try:
            with self.connection:
                cursor = self.connection.execute(
                    "SELECT id FROM city WHERE name = ?",
                    (city_name,)
                )
                row = cursor.fetchone()
                return row["id"] if row else None
        except Exception as e:
            print(f"Ошибка при получении ID города: {e}")
            return None

    def get_country_id_from_city_id(self, city_id):
        try:
            with self.connection:
                cursor = self.connection.execute(
                    "SELECT country_id FROM city WHERE id = ?",
                    (city_id,)
                )
                row = cursor.fetchone()
                return row["country_id"] if row else None
        except Exception as e:
            print(f"Ошибка при получении ID страны: {e}")
            return None

    def add_user(self, nickname, city_name, password):
        try:
            hashed = hash_password(password).decode('utf-8')
            with self.connection:
                # проверка на существование
                cursor = self.connection.execute(
                    "SELECT COUNT(*) FROM customer WHERE name = ?",
                    (nickname,)
                )
                if cursor.fetchone()[0] > 0:
                    print(f"Пользователь '{nickname}' уже существует.")
                    return
                # получение city_id / country_id
                city_id = self.get_city_id_from_city_name(city_name)
                country_id = self.get_country_id_from_city_id(city_id)
                # вставка
                self.connection.execute(
                    """
                    INSERT INTO customer (name, city_id, country_id, password_user)
                    VALUES (?, ?, ?, ?)
                    """,
                    (nickname, city_id, country_id, hashed)
                )
                print(f"Пользователь '{nickname}' успешно добавлен.")
        except Exception as e:
            print(f"Ошибка при добавлении пользователя: {e}")

    def get_user_id_from_nickname(self, nickname):
        try:
            with self.connection:
                cursor = self.connection.execute(
                    "SELECT id FROM customer WHERE name = ?",
                    (nickname,)
                )
                row = cursor.fetchone()
                return row["id"] if row else None
        except Exception as e:
            print(f"Ошибка при получении ID пользователя: {e}")
            return None

    def get_user_password(self, user_id):
        try:
            with self.connection:
                cursor = self.connection.execute(
                    "SELECT password_user FROM customer WHERE id = ?",
                    (user_id,)
                )
                row = cursor.fetchone()
                return row["password_user"] if row else None
        except Exception as e:
            print(f"Ошибка при получении пароля пользователя: {e}")
            return None

    def get_city_name_from_user_id(self, user_id):
        try:
            with self.connection:
                cursor = self.connection.execute(
                    "SELECT name FROM city "
                    "WHERE id = (SELECT city_id FROM customer WHERE id = ?)",
                    (user_id,)
                )
                row = cursor.fetchone()
                return row["name"] if row else None
        except Exception as e:
            print(f"Ошибка при получении названия города: {e}")
            return None

    def get_user_rating(self, user_id):
        try:
            with self.connection:
                cursor = self.connection.execute(
                    "SELECT rating FROM customer WHERE id = ?",
                    (user_id,)
                )
                row = cursor.fetchone()
                return row["rating"] if row and row["rating"] else 0
        except Exception as e:
            print(f"Ошибка при получении рейтинга пользователя: {e}")
            return 0

    def get_time_to_take_attractions_from_user_id(self, user_id):
        try:
            with self.connection:
                cursor = self.connection.execute(
                    "SELECT time_to_take_attractions FROM customer WHERE id = ?",
                    (user_id,)
                )
                row = cursor.fetchone()
                val = row["time_to_take_attractions"] if row else None
                if not val:
                    return 0
                # пытаемся распарсить ISO-строку, иначе число
                try:
                    return datetime.fromisoformat(val).timestamp()
                except ValueError:
                    return float(val)
        except Exception as e:
            print(f"Ошибка при получении времени получения достопримечательности: {e}")
            return 0

    def get_coords_from_attractions_id(self, attr_id):
        try:
            with self.connection:
                cursor = self.connection.execute(
                    "SELECT latitude, longitude FROM attractions WHERE id = ?",
                    (attr_id,)
                )
                row = cursor.fetchone()
                return (row["latitude"], row["longitude"]) if row else (None, None)
        except Exception as e:
            print(f"Ошибка при получении координат достопримечательности: {e}")
            return None, None

    def get_set_dedicated_attractions(self, user_id):
        try:
            with self.connection:
                cursor = self.connection.execute(
                    "SELECT dedicated_attractions FROM customer WHERE id = ?",
                    (user_id,)
                )
                row = cursor.fetchone()
                s = row["dedicated_attractions"] if row else ""
                return set(s.split()) if s else set()
        except Exception as e:
            print(f"Ошибка при получении набора посвящённых достопримечательностей: {e}")
            return set()

    def get_city_id_from_user_id(self, user_id):
        try:
            with self.connection:
                cursor = self.connection.execute(
                    "SELECT city_id FROM customer WHERE id = ?",
                    (user_id,)
                )
                row = cursor.fetchone()
                return row["city_id"] if row else None
        except Exception as e:
            print(f"Ошибка при получении ID города пользователя: {e}")
            return None

    def get_random_attractions_from_user(self, user_id):
        try:
            city_id = self.get_city_id_from_user_id(user_id)
            with self.connection:
                cursor = self.connection.execute(
                    "SELECT id FROM attractions WHERE city_id = ?",
                    (city_id,)
                )
                all_ids = [str(r["id"]) for r in cursor.fetchall()]
            dedicated = self.get_set_dedicated_attractions(user_id)
            available = set(all_ids) - dedicated
            return random.choice(list(available)) if available else None
        except Exception as e:
            print(f"Ошибка при получении случайной достопримечательности: {e}")
            return None

    def give_user_attractions(self, user_id, attractions_id, time_take_attractions, selection_type):
        try:
            ts = datetime.utcfromtimestamp(time_take_attractions).isoformat()
            with self.connection:
                self.connection.execute(
                    """
                    UPDATE customer
                    SET attractions_now = ?, time_to_take_attractions = ?, selection_type = ?
                    WHERE id = ?
                    """,
                    (attractions_id, ts, selection_type, user_id)
                )
        except Exception as e:
            print(f"Ошибка при назначении достопримечательности пользователю: {e}")

    def get_all_users_list(self):
        try:
            with self.connection:
                cursor = self.connection.execute(
                    "SELECT name, COALESCE(rating,0) AS rating "
                    "FROM customer ORDER BY rating DESC LIMIT 10"
                )
                return [(r["name"], r["rating"]) for r in cursor.fetchall()]
        except Exception as e:
            print(f"Ошибка при получении списка пользователей: {e}")
            return []

    def get_attractions_now_from_user(self, user_id):
        """
        Возвращает ID текущей достопримечательности, выбранной пользователем.
        :param user_id: ID пользователя
        :return: ID достопримечательности или None
        """
        try:
            with self.connection:
                cursor = self.connection.execute(
                    """
                    SELECT attractions_now
                    FROM customer
                    WHERE id = ?
                    """, (user_id,)
                )
                row = cursor.fetchone()
                if row and row["attractions_now"] is not None:
                    return row["attractions_now"]
                else:
                    return None
        except Exception as e:
            print(f"Ошибка при получении ID текущей достопримечательности пользователя: {e}")
            return None

    def get_url_image_from_attractions_id(self, attraction_id):
        """
        Возвращает URL первого фото для достопримечательности с данным ID.
        Если фотографий нет или произошла ошибка — возвращает None.
        """
        try:
            with self.connection:
                cursor = self.connection.execute(
                    "SELECT url FROM attractions_photo WHERE attraction_id = ?",
                    (attraction_id,)
                )
                row = cursor.fetchone()
                return row["url"] if row else None
        except Exception as e:
            print(f"Ошибка при получении URL изображения достопримечательности: {e}")
            return None
    def get_all_info_about_attractions(self, attraction_id):
        """
        Возвращает список записей таблицы attractions для данного attraction_id.
        Обычно это список из одного кортежа (или sqlite3.Row), либо пустой список.
        """
        try:
            with self.connection:
                cursor = self.connection.execute(
                    "SELECT * FROM attractions WHERE id = ?",
                    (attraction_id,)
                )
                return cursor.fetchall()  # список строк, каждая строка — tuple/Row
        except Exception as e:
            print(f"Ошибка при получении информации о достопримечательности: {e}")
            return []

    def remove_current_attraction(self, user_id):
        """
        Удаляет текущую достопримечательность у пользователя, устанавливая `attractions_now` в NULL.
        """
        try:
            with self.connection:
                self.connection.execute(
                    """
                    UPDATE customer
                    SET attractions_now = NULL
                    WHERE id = ?
                    """,
                    (user_id,)
                )
                print(f"Текущая достопримечательность для пользователя {user_id} была удалена.")
        except Exception as e:
            print(f"Ошибка при удалении текущей достопримечательности пользователя: {e}")

    def add_to_dedicated_attractions(self, user_id, attraction_id):
        """
        Добавляет достопримечательность в поле dedicated_attractions для пользователя.
        Если достопримечательность уже есть, то она не будет добавлена повторно.
        """
        try:
            # Получаем текущий набор посвящённых достопримечательностей
            dedicated_attractions = self.get_set_dedicated_attractions(user_id)

            # Добавляем новую достопримечательность в set
            dedicated_attractions.add(str(attraction_id))

            # Преобразуем set обратно в строку (с разделением пробелами)
            new_dedicated_attractions = " ".join(dedicated_attractions)

            # Обновляем поле dedicated_attractions в таблице customer
            with self.connection:
                self.connection.execute(
                    """
                    UPDATE customer
                    SET dedicated_attractions = ?
                    WHERE id = ?
                    """,
                    (new_dedicated_attractions, user_id)
                )
                print(f"Достопримечательность {attraction_id} была добавлена в посвящённые для пользователя {user_id}.")
        except Exception as e:
            print(f"Ошибка при добавлении достопримечательности в dedicated_attractions пользователя: {e}")

    def get_selection_type_from_user(self, user_id):
        """
        Возвращает значение поля selection_type для данного пользователя.
        Если запись не найдена или произошла ошибка — возвращает None.
        """
        try:
            with self.connection:
                cursor = self.connection.execute(
                    "SELECT selection_type FROM customer WHERE id = ?",
                    (user_id,)
                )
                row = cursor.fetchone()
                return row["selection_type"] if row else None
        except Exception as e:
            print(f"Ошибка при получении selection_type пользователя: {e}")
            return None


    def save_photo_for_moderation(self, filepath, filename, user_id):
        """
        Сохраняет фотографию в таблице attractions_photo для модерации.
        Задача: сохранять путь к файлу и связывать его с пользователем.
        """
        try:
            # Генерация полного пути для хранения файла
            file_path = os.path.join(filepath, filename)

            # Вставляем запись о фото в таблицу attractions_photo
            with self.connection:
                self.connection.execute(
                    """
                    INSERT INTO attractions_photo (url, attraction_id)
                    VALUES (?, ?)
                    """,
                    (file_path, user_id)  # Предположим, что attraction_id = user_id
                )
            print(f"Фото для модерации успешно добавлено для пользователя {user_id}")
        except Exception as e:
            print(f"Ошибка при сохранении фотографии для модерации: {e}")

    def get_attractions_by_city_id(self, city_id):
        try:
            cursor = self.connection.cursor()
            try:
                cursor.execute("""
                    SELECT id, name, description, address, latitude, longitude
                    FROM attractions
                    WHERE city_id = ?
                """, (city_id,))
                return cursor.fetchall()
            finally:
                cursor.close()
        except Exception as e:
            print(f"Ошибка при получении достопримечательностей по city_id={city_id}: {e}")
            return []

    def update_user_rating(self, user_id: int, points: int) -> bool:
        """
        Прибавляет к рейтингу пользователя заданное число очков.

        :param user_id: ID пользователя
        :param points: количество очков для прибавления (может быть отрицательным)
        :return: True при успешном обновлении, False при ошибке
        """
        try:
            # Сначала достаём текущий рейтинг (метод возвращает 0, если рейтинга ещё нет)
            current = self.get_user_rating(user_id)
            new_rating = current + points

            # Сохраняем обновлённый рейтинг
            with self.connection:
                self.connection.execute(
                    "UPDATE customer SET rating = ? WHERE id = ?",
                    (new_rating, user_id)
                )
            return True
        except Exception as e:
            print(f"Ошибка при обновлении рейтинга пользователя {user_id}: {e}")
            return False

    def change_city_from_user(self, user_id: int, city_id: int):
        """
        Изменяет значение поля city_id для данного пользователя.

        :param user_id: ID пользователя
        :param city_id: Новый ID города
        :return: True при успешном обновлении, False при ошибке
        """
        try:
            with self.connection:
                self.connection.execute(
                    "UPDATE customer SET city_id = ? WHERE id = ?",
                    (city_id, user_id))

        except Exception as e:
            print(f"Ошибка при изменении города пользователя {user_id}: {e}")




