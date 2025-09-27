import os  # Работа с файловой системой
import asyncio  # Асинхронное программирование (async/await)
import random  # Генерация случайных чисел (например, выбор кандидата)
import json  # Сериализация и десериализация данных в формате JSON
import uuid  # Генерация уникальных идентификаторов (например, для имен файлов)
from pathlib import Path  # Удобная работа с путями к файлам и директориями
import aiosqlite  # Асинхронное взаимодействие с SQLite базой данных
from aiogram import Bot, Dispatcher, types, F  # Основные классы для работы с Telegram-ботом
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove  # Классы для создания клавиатур
from aiogram.filters import Command  # Фильтр для обработки команд (например, /start)
from aiogram.fsm.storage.memory import MemoryStorage  # Хранилище состояний (FSM) в памяти
from aiogram.fsm.state import State, StatesGroup  # Определение состояний конечного автомата
from aiogram.fsm.context import FSMContext  # Контекст для работы с данными состояний
from dotenv import load_dotenv  # Загрузка переменных окружения

# Загружаем переменные окружения
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")  # Получаем токен из переменных окружения
DB_FILE = "database/users.db"  # Файл базы данных SQLite
PHOTO_DIR = "database/photos"  # Директория для хранения фотографий пользователей

INTEREST_OPTIONS = [                                                                                                    #<--------------------- Допчик
    "Жаворонок 🐦",
    "Сова 🦉",
    "Чистюля 🧹",
    "Не боюсь беспорядка 🛋️",
    "Люблю готовить 🍳",
    "Живу доставками 🍕",
    "Тишина и покой 🤫",
    "Шумный и весёлый 🎉",
    "Курю 🚬",
    "Против курения 🚭",
    "Любитель растений 🌿",
    "Любитель музыки 🎧",
    "Тишина в доме 🔇",
    "Любитель фильмов 🎬",
    "Геймер 🎮",
    "Фитнес-энтузиаст 💪",
    "Любитель йоги 🧘",
    "Кофеман ☕",
    "Чайный гурман 🫖",
    "Ночной перекус 🌙",
    "Любитель настолок 🎲",
    "Книжный червь 📚",
    "Творческая личность 🎨",
    "Технарь 🤖",
    "Любитель тихих вечеров 🕯️",
    "Любитель активного отдыха 🏞️",
]

# Создаем необходимые директории, если они не существуют
Path("database").mkdir(parents=True, exist_ok=True)
Path(PHOTO_DIR).mkdir(parents=True, exist_ok=True)

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Определяем состояния для редактора анкеты
class EditProfile(StatesGroup):
    waiting_for_choice = State()                # Главное меню редактора
    waiting_for_new_name = State()              # Ожидание нового имени
    waiting_for_new_age = State()               # Ожидание нового возраста
    waiting_for_new_gender = State()            # Ожидание нового выбора пола
    waiting_for_new_photo = State()             # Ожидание нового фото
    waiting_for_new_preferred_gender = State()  # Ожидание нового предпочитаемого пола
    waiting_for_new_interests = State()         # Новое состояние для выбора интересов
    waiting_for_filter_min_age = State()        # Ожидание минимального возраста для фильтра
    waiting_for_filter_max_age = State()        # Ожидание максимального возраста для фильтра
    waiting_for_filter_interests = State()      # Ожидание выбора интересов для фильтра

# Функция для создания клавиатуры с кнопкой "Все равно"
def get_anyway_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Все равно")]],
        resize_keyboard=True
    )

# Обработчик для кнопки "Фильтры" в меню редактора
@dp.message(EditProfile.waiting_for_choice, F.text == "Фильтры")
async def start_filters(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    # Проверяем премиум статус пользователя
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT premium FROM users WHERE id = ?", (user_id,)) as cursor:
            result = await cursor.fetchone()
            is_premium = result[0] if result else False

    if not is_premium:
        # Если у пользователя нет премиума, предлагаем его купить
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Купить премиум")],
                [KeyboardButton(text="Вернуться в главное меню")]
            ],
            resize_keyboard=True
        )
        await message.answer(
            "Фильтры доступны только с премиум-подпиской!\n\n"
            "Премиум-подписка позволяет:\n"
            "• Настраивать фильтры по возрасту\n"
            "• Фильтровать по интересам\n"
            "• Получать более точные совпадения\n\n"
            "Хотите приобрести премиум-подписку?",
            reply_markup=kb
        )
        return

    # Если у пользователя есть премиум, продолжаем как обычно
    await state.set_state(EditProfile.waiting_for_filter_min_age)
    await message.answer("Укажите минимальный возраст (от 17 до 27):", reply_markup=get_anyway_keyboard())

# Обработчик для минимального возраста
@dp.message(EditProfile.waiting_for_filter_min_age)
async def process_filter_min_age(message: types.Message, state: FSMContext):
    if message.text == "Все равно":
        await state.update_data(filter_min_age=None)
    else:
        if not message.text.isdigit():
            await message.answer("Пожалуйста, введите число или нажмите 'Все равно'")
            return
        age = int(message.text)
        if age < 17 or age > 27:
            await message.answer("Возраст должен быть от 17 до 27 лет")
            return
        await state.update_data(filter_min_age=age)
    
    await state.set_state(EditProfile.waiting_for_filter_max_age)
    await message.answer("Укажите максимальный возраст (от 17 до 27):", reply_markup=get_anyway_keyboard())

# Обработчик для максимального возраста
@dp.message(EditProfile.waiting_for_filter_max_age)
async def process_filter_max_age(message: types.Message, state: FSMContext):
    if message.text == "Все равно":
        await state.update_data(filter_max_age=None)
    else:
        if not message.text.isdigit():
            await message.answer("Пожалуйста, введите число или нажмите 'Все равно'")
            return
        age = int(message.text)
        if age < 17 or age > 27:
            await message.answer("Возраст должен быть от 17 до 27 лет")
            return
        await state.update_data(filter_max_age=age)
    
    await state.set_state(EditProfile.waiting_for_filter_interests)
    await message.answer("Выберите предпочитаемые интересы (можно выбрать несколько):", reply_markup=get_interests_keyboard())

# Обработчик для выбора интересов в фильтрах
@dp.message(EditProfile.waiting_for_filter_interests)
async def process_filter_interests(message: types.Message, state: FSMContext):
    text = message.text
    if text == "Завершить выбор":
        # Получаем все данные фильтров
        data = await state.get_data()
        filter_data = {
            "min_age": data.get("filter_min_age"),
            "max_age": data.get("filter_max_age"),
            "interests": data.get("filter_interests", [])
        }
        
        # Сохраняем фильтры в базу данных
        user_id = message.from_user.id
        await update_user_field(user_id, "filters", json.dumps(filter_data))
        
        await state.set_state(EditProfile.waiting_for_choice)
        await message.answer("Фильтры успешно сохранены!", reply_markup=get_edit_menu_keyboard())
        return

    if text in INTEREST_OPTIONS:
        user_data = await state.get_data()
        interests = user_data.get("filter_interests", [])
        if text not in interests:
            interests.append(text)
            await state.update_data(filter_interests=interests)
            await message.answer(f"Интерес '{text}' добавлен. Выбрано: {', '.join(interests)}")
        else:
            await message.answer("Этот интерес уже выбран.")
    else:
        await message.answer("Неверный выбор. Пожалуйста, выберите интерес из предложенных вариантов или нажмите 'Завершить выбор'.")

# Определяем состояния для регистрации пользователя с измененным порядком вопросов
class Registration(StatesGroup):
    waiting_for_name = State()              # Ввод имени
    waiting_for_age = State()               # Ввод возраста
    waiting_for_gender = State()            # Выбор пола
    waiting_for_text = State()              # Описание (био)
    waiting_for_photo = State()             # Загрузка фото
    waiting_for_interests = State()         # Выбор интересов                                                                <--------------------- Допчик
    waiting_for_preferred_gender = State()  # Вопрос "Кого вы ищете?" с новыми кнопками
    waiting_for_premium = State()           # Этап про премиум

# Определяем состояния для просмотра анкет
class DatingStates(StatesGroup):
    viewing_profiles = State()  # Состояние просмотра анкет кандидатов

# Функция для создания клавиатуры главного меню
def get_main_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Смотреть анкеты"), KeyboardButton(text="Редактировать анкету")]
            # [KeyboardButton(text="Редактировать анкету")]

        ],
        resize_keyboard=True
    )

def get_main_menu_unregistered():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Создать анкету")]],
        resize_keyboard=True
    )

# Функция для создания клавиатуры выбора пола (изменено)
def get_gender_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Я парень"), KeyboardButton(text="Я девушка")]
        ],
        resize_keyboard=True
    )

# Функция для создания клавиатуры выбора интересов                                                                    <--------------------- Допчик
def get_interests_keyboard():
    buttons = []
    for interest in INTEREST_OPTIONS:
        buttons.append([KeyboardButton(text=interest)])
    buttons.append([KeyboardButton(text="Завершить выбор")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)  # Убрали one_time_keyboard


# Функция для создания клавиатуры с действиями над анкетой с кнопками Лайк, Дизлайк, Пропустить и Вернуться в главное меню
def get_profile_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❤️ Лайк"), KeyboardButton(text="👎 Дизлайк")],
            [KeyboardButton(text="Вернуться в главное меню")]
        ],
        resize_keyboard=True
    )


async def delete_user_profile(user_id: int):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        await db.commit()

# Функция для создания клавиатуры с кнопкой "Смотреть анкеты" (при необходимости)
def get_view_profiles_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="👀 Смотреть анкеты")]],
        resize_keyboard=True
    )

# Функция для создания клавиатуры редактора анкеты
def get_edit_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Изменить имя"), KeyboardButton(text="Изменить возраст")],
            [KeyboardButton(text="Изменить пол"), KeyboardButton(text="Изменить фото")],
            [KeyboardButton(text="Изменить предпочитаемый пол"), KeyboardButton(text="Изменить интересы")],
            [KeyboardButton(text="Фильтры")],  # Новая кнопка
            [KeyboardButton(text="Заполнить анкету заново")],  # Новая кнопка
            [KeyboardButton(text="Вернуться в главное меню")]
        ],
        resize_keyboard=True
    )



# Функция для проверки, существует ли пользователь в базе данных
async def user_exists(user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT id FROM users WHERE id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row is not None

# Асинхронная функция для инициализации базы данных
async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        # Создаем таблицу с полной схемой
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT,
                age INTEGER,
                gender TEXT,
                preferred_gender TEXT,
                bio TEXT,
                photo TEXT,
                liked TEXT DEFAULT '[]',
                disliked TEXT DEFAULT '[]',
                match TEXT DEFAULT '[]',
                premium BOOLEAN DEFAULT FALSE,
                interests TEXT DEFAULT '[]',
                filters TEXT DEFAULT '{}'
            )
        ''')
        
        # Проверяем, есть ли колонки interests и filters, если нет - добавляем
        async with db.execute("PRAGMA table_info(users)") as cursor:
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            if 'interests' not in column_names:
                await db.execute("ALTER TABLE users ADD COLUMN interests TEXT DEFAULT '[]'")
                print("Добавлена колонка 'interests'")
            
            if 'filters' not in column_names:
                await db.execute("ALTER TABLE users ADD COLUMN filters TEXT DEFAULT '{}'")
                print("Добавлена колонка 'filters'")
        
        await db.commit()

# Вызываем инициализацию базы данных
asyncio.run(init_db())

# Функция для обновления отдельного поля пользователя в базе данных
async def update_user_field(user_id, field, value):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(f"UPDATE users SET {field} = ? WHERE id = ?", (value, user_id))
        await db.commit()

# Функция для отправки полной анкеты пользователя после внесения изменений                                                                        #<-------------------- тут немного допов
async def send_full_profile(user_id, message: types.Message):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT name, age, gender, preferred_gender, bio, photo, interests FROM users WHERE id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
    if row:
        name, age, gender, preferred_gender, bio, photo, interests = row
        interests_list = json.loads(interests) if interests else []
        # Если список пуст, выводим прочерк
        interests_text = '\n' + '\n'.join(f"• {interest}" for interest in interests_list) if interests_list else "-"
        caption = (
            f"👤 Имя: {name}\n"
            f"🎂 Возраст: {age}\n"
            f"🚻 Пол: {gender}\n"
            f"🔎 Предпочитаемый: {preferred_gender}\n"
            f"📝 О себе: {bio}\n"
            f"🎯 Интересы: {interests_text}"
        )
        try:
            with open(photo, 'rb') as photo_file:
                await message.answer_photo(
                    types.BufferedInputFile(photo_file.read(), filename="profile.jpg"),
                    caption=caption,
                    reply_markup=get_edit_menu_keyboard()
                )
        except Exception as e:
            await message.answer(caption, reply_markup=get_edit_menu_keyboard())


# Асинхронная функция для сохранения данных пользователя в базу данных                                                 #<-------------------- тут немного допов
async def save_user(user_id, name, age, gender, preferred_gender, bio, photo, interests): 
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('''
            INSERT OR REPLACE INTO users (id, name, age, gender, preferred_gender, bio, photo, liked, disliked, match, interests)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, name, age, gender, preferred_gender, bio, photo, "[]", "[]", "[]", json.dumps(interests)))
        await db.commit()

# Асинхронная функция для получения списка кандидатов с учетом фильтров
async def get_users(user_id, preferred_gender):
    async with aiosqlite.connect(DB_FILE) as db:
        # Получаем фильтры пользователя
        async with db.execute("SELECT filters FROM users WHERE id = ?", (user_id,)) as cursor:
            filters_row = await cursor.fetchone()
        
        filters = json.loads(filters_row[0]) if filters_row and filters_row[0] else {}
        
        # Базовый запрос
        query = "SELECT id, name, age, gender, bio, photo, interests FROM users WHERE id != ?"
        params = [user_id]
        
        # Добавляем фильтр по полу
        if preferred_gender != "Все":
            query += " AND gender = ?"
            params.append(preferred_gender)
        
        # Добавляем фильтр по возрасту
        if filters.get("min_age"):
            query += " AND age >= ?"
            params.append(filters["min_age"])
        if filters.get("max_age"):
            query += " AND age <= ?"
            params.append(filters["max_age"])
        
        # Получаем всех кандидатов
        async with db.execute(query, params) as cursor:
            candidates = await cursor.fetchall()
        
        # Фильтруем по интересам, если они указаны
        if filters.get("interests"):
            filtered_candidates = []
            for candidate in candidates:
                candidate_interests = json.loads(candidate[6]) if candidate[6] else []
                # Проверяем, есть ли хотя бы один общий интерес
                if any(interest in candidate_interests for interest in filters["interests"]):
                    filtered_candidates.append(candidate)
            return filtered_candidates
        
        return candidates


# Асинхронная функция для получения списков реакций (liked, disliked, match) для пользователя
async def get_user_reactions(user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT liked, disliked, match FROM users WHERE id = ?", (user_id,)) as cursor:
            result = await cursor.fetchone()
    liked_list, disliked_list, match_list = [], [], []
    if result:
        try:
            liked_list = json.loads(result[0])
        except Exception:
            liked_list = []
        try:
            disliked_list = json.loads(result[1])
        except Exception:
            disliked_list = []
        try:
            match_list = json.loads(result[2])
        except Exception:
            match_list = []
    return liked_list, disliked_list, match_list

# Функция для проверки взаимного лайка:
# Если в поле liked пользователя (кандидата) уже содержится ID текущего пользователя, возвращается True.
async def is_mutual_like(user_id, candidate_id):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT liked FROM users WHERE id = ?", (candidate_id,)) as cursor:
            result = await cursor.fetchone()
    if result:
        try:
            candidate_likes = json.loads(result[0])
        except Exception:
            candidate_likes = []
        return user_id in candidate_likes
    return False

# Асинхронная функция для добавления ID кандидата в поле match пользователя
async def add_match(user_id, candidate_id):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT match FROM users WHERE id = ?", (user_id,)) as cursor:
            result = await cursor.fetchone()
        if result is None:
            return
        try:
            current_list = json.loads(result[0])
        except Exception:
            current_list = []
        if candidate_id not in current_list:
            current_list.append(candidate_id)
        new_list_str = json.dumps(current_list)
        await db.execute("UPDATE users SET match = ? WHERE id = ?", (new_list_str, user_id))
        await db.commit()


# Новая функция: отправляет полную анкету пользователя с идентификатором profile_owner_id
# в чат recipient_chat_id.
async def send_profile_to_candidate(profile_owner_id, recipient_chat_id):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute(
            "SELECT name, age, gender, preferred_gender, bio, photo, interests FROM users WHERE id = ?",
            (profile_owner_id,)
        ) as cursor:
            row = await cursor.fetchone()
    if row:
        name, age, gender, preferred_gender, bio, photo, interests = row
        interests_list = json.loads(interests) if interests else []
        interests_text = '\n' + '\n'.join(f"• {interest}" for interest in interests_list) if interests_list else "-"
        caption = (
            f"👤 Имя: {name}\n"
            f"🎂 Возраст: {age}\n"
            f"🚻 Пол: {gender}\n"
            f"🔎 Предпочитаемый: {preferred_gender}\n"
            f"📝 О себе: {bio}\n"
            f"🎯 Интересы: {interests_text}"
        )
        try:
            with open(photo, 'rb') as photo_file:
                await bot.send_photo(recipient_chat_id, photo=photo_file.read(), caption=caption)
        except Exception as e:
            await bot.send_message(recipient_chat_id, caption)

# Асинхронная функция для получения имени пользователя по его ID
async def get_user_name(user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT name FROM users WHERE id = ?", (user_id,)) as cursor:
            result = await cursor.fetchone()
        return result[0] if result else "Пользователь"

# Асинхронная функция для показа следующей анкеты с учетом фильтров
async def show_next_profile(user_id, message: types.Message):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT preferred_gender FROM users WHERE id = ?", (user_id,)) as cursor:
            result = await cursor.fetchone()
    preferred_gender = result[0] if result else "Все"
    
    candidates = await get_users(user_id, preferred_gender)
    liked_list, disliked_list, match_list = await get_user_reactions(user_id)
    excluded = set(liked_list + disliked_list + match_list)
    filtered_candidates = [candidate for candidate in candidates if candidate[0] not in excluded]
    
    if not filtered_candidates:
        await message.answer("Анкеты для просмотра закончились!", reply_markup=get_main_menu_keyboard())
        return
    
    candidate = random.choice(filtered_candidates)
    candidate_id, name, age, gender, bio, photo, interests = candidate
    interests_list = json.loads(interests) if interests else []
    interests_text = '\n' + '\n'.join(f"• {interest}" for interest in interests_list) if interests_list else "-"
    
    try:
        with open(photo, 'rb') as photo_file:
            caption = (
                f"👤 Имя: {name}\n"
                f"🎂 Возраст: {age}\n"
                f"🚻 Пол: {gender}\n"
                f"📝 О себе: {bio}\n"
                f"🎯 Интересы: {interests_text}"
            )
            await message.answer_photo(
                types.BufferedInputFile(photo_file.read(), filename="profile.jpg"),
                caption=caption,
                reply_markup=get_profile_keyboard()
            )
            print(f"Показана анкета пользователя {candidate_id}")
            return candidate_id
    except Exception as e:
        print(f"Ошибка при показе анкеты: {e}")
        return await show_next_profile(user_id, message)

# Асинхронная функция для добавления реакции (лайк или дизлайк) к анкете
async def add_reaction(user_id, candidate_id, like=True):
    field = "liked" if like else "disliked"
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute(f"SELECT {field} FROM users WHERE id = ?", (user_id,)) as cursor:
            result = await cursor.fetchone()
        if result is None:
            return
        try:
            current_list = json.loads(result[0])
        except Exception:
            current_list = []
        if candidate_id not in current_list:
            current_list.append(candidate_id)
        new_list_str = json.dumps(current_list)
        await db.execute(f"UPDATE users SET {field} = ? WHERE id = ?", (new_list_str, user_id))
        await db.commit()

# Обработчик команды /start: проверяет, существует ли пользователь в базе
@dp.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if await user_exists(user_id):
        await message.answer("Главное меню:", reply_markup=get_main_menu_keyboard())
    else:
        await message.answer(
            "Привет! С помощью этого бота ты легко сможешь найти соседа для съёмной квартиры!\n"
            "Сначала необходимо создать анкету.",
            reply_markup=get_main_menu_unregistered()
        )

# Обработчик для начала регистрации (если нужно создать анкету)
@dp.message(F.text == "Создать анкету")
async def register_command(message: types.Message, state: FSMContext):
    await state.set_state(Registration.waiting_for_name)
    await message.answer("Как тебя зовут?", reply_markup=ReplyKeyboardRemove())

# Обработчик состояния ожидания имени: сохраняет имя и переходит к вводу возраста
@dp.message(Registration.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(Registration.waiting_for_age)
    await message.answer("Сколько тебе лет?")

# Обработчик состояния ожидания возраста: проверяет ввод, фильтрует возраст и сохраняет его
@dp.message(Registration.waiting_for_age, F.text==True)
@dp.message(Registration.waiting_for_age)
async def process_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введи корректный возраст (число).")
        return
    age = int(message.text)
    # Фильтрация: если возраст меньше 18 или больше 27, регистрация прекращается
    if age < 16 or age > 27:                                                                            # возраст меньше 17 поставил, чтобы было включительно 
        await message.answer("Наш бот подходит исключительно для молодых людей!\nДоступный возраст от 17 до 27 лет")
        await state.clear()
        return
    await state.update_data(age=age)
    await state.set_state(Registration.waiting_for_gender)
    await message.answer("Укажи свой пол", reply_markup=get_gender_keyboard())

# Обработчик выбора пола: изменен для кнопок "Я парень" и "Я девушка"
@dp.message(Registration.waiting_for_gender, F.text.in_(["Я парень", "Я девушка"]))
async def process_gender(message: types.Message, state: FSMContext):
    if message.text == "Я парень":
        gender = "Мужской"
    else:
        gender = "Женский"
    await state.update_data(gender=gender)
    await state.set_state(Registration.waiting_for_text)
    await message.answer("Напиши немного о себе:", reply_markup=ReplyKeyboardRemove())

# Обработчик ввода описания: сохраняет текст и переходит к ожиданию фото
@dp.message(Registration.waiting_for_text)
async def process_text(message: types.Message, state: FSMContext):
    await state.update_data(bio=message.text.strip())
    await state.set_state(Registration.waiting_for_photo)
    await message.answer("Прикрепи свою фотографию")

# Обработчик для перехода к выбору интересов после загрузки фото                                    <------------------------------- отсюда начало допа
@dp.message(Registration.waiting_for_photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    photo = message.photo[-1]
    user_id = message.from_user.id
    photo_filename = f"{user_id}_{uuid.uuid4().hex}.jpg"
    photo_path = f"{PHOTO_DIR}/{photo_filename}"
    file_info = await bot.get_file(photo.file_id)
    await bot.download_file(file_info.file_path, destination=Path(photo_path))
    print(f"Фото сохранено по пути: {photo_path}")
    await state.update_data(photo=photo_path)
    await state.set_state(Registration.waiting_for_interests)
    await message.answer("Выбери до пяти интересов, которые тебе подходят:", reply_markup=get_interests_keyboard())

# Обработчик для выбора интересов
@dp.message(Registration.waiting_for_interests)
async def process_interests(message: types.Message, state: FSMContext):
    text = message.text
    if text == "Завершить выбор":
        user_data = await state.get_data()
        interests = user_data.get("interests", [])
        if not interests:
            await message.answer("Пожалуйста, выберите хотя бы один интерес.")
            return
            
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Парня"), KeyboardButton(text="Девушку"), KeyboardButton(text="Все равно")]
            ],
            resize_keyboard=True
        )
        await state.set_state(Registration.waiting_for_preferred_gender)
        await message.answer("Кого ты ищешь в качестве соседа?", reply_markup=kb)
        return

    if text in INTEREST_OPTIONS:
        user_data = await state.get_data()
        interests = user_data.get("interests", [])
        
        if len(interests) >= 5:
            await message.answer("Вы уже выбрали максимальное количество интересов (5). Нажмите 'Завершить выбор'.")
            return
            
        if text not in interests:
            interests.append(text)
            await state.update_data(interests=interests)
            await message.answer(f"Интерес '{text}' добавлен. Выбрано: {', '.join(interests)}")
            
            if len(interests) >= 5:
                kb = ReplyKeyboardMarkup(
                    keyboard=[
                        [KeyboardButton(text="Парня"), KeyboardButton(text="Девушку"), KeyboardButton(text="Все равно")]
                    ],
                    resize_keyboard=True
                )
                await state.set_state(Registration.waiting_for_preferred_gender)
                await message.answer("Ты выбрал максимальное количество интересов. Теперь выбери, кого ты ищешь в качестве соседа:", reply_markup=kb)
        else:
            await message.answer("Этот интерес уже выбран.")
    else:
        await message.answer("Неверный выбор. Пожалуйста, выберите интерес из предложенных вариантов или нажмите 'Завершить выбор'.")

# Новый обработчик выбора предпочитаемого кандидата (с маппингом значений для БД)
@dp.message(Registration.waiting_for_preferred_gender, F.text.in_(["Парня", "Девушку", "Все равно"]))
async def process_preferred_gender_new(message: types.Message, state: FSMContext):
    pref = message.text
    if pref == "Парня":
        mapped = "Мужской"
    elif pref == "Девушку":
        mapped = "Женский"
    else:
        mapped = "Все"
    await state.update_data(preferred_gender=mapped)
    
    # Предлагаем премиум-подписку
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Купить премиум")],
            [KeyboardButton(text="Давай пока без него")]
        ],
        resize_keyboard=True
    )
    await state.set_state(Registration.waiting_for_premium)
    await message.answer(
        "🌟 Хочешь узнать о преимуществах премиум-подписки?\n\n"
        "✨ С премиум-подпиской ты получишь:\n"
        "• 🎯 Доступ к фильтрам по возрасту\n"
        "• 🎨 Фильтрацию по интересам\n"
        "• 💫 Более точные совпадения\n"
        "• ⚡ Приоритет в поиске\n\n"
        "💰 Стоимость: 149 рублей в месяц\n\n"
        "Что выбираешь?",
        reply_markup=kb
    )

# Обработчик этапа премиум
@dp.message(Registration.waiting_for_premium, F.text.in_(["Купить премиум", "Давай пока без него"]))
async def process_premium(message: types.Message, state: FSMContext):
    choice = message.text
    if choice == "Купить премиум":
        await message.answer(
            "🌟 Премиум-подписка\n\n"
            "✨ Включает:\n"
            "• 🎯 Доступ к фильтрам по возрасту\n"
            "• 🎨 Фильтрацию по интересам\n"
            "• 💫 Более точные совпадения\n"
            "• ⚡ Приоритет в поиске\n\n"
            "💰 Стоимость: 149 рублей в месяц\n\n"
            "К сожалению, функция покупки премиум-подписки пока находится в разработке.\n"
            "Следите за обновлениями!",
            reply_markup=get_edit_menu_keyboard()
        )
    else:  # "Давай пока без него"
        # Финализируем регистрацию: сохраняем данные в БД
        data = await state.get_data()
        user_id = message.from_user.id
        await save_user(
            user_id,
            data["name"],
            data["age"],
            data["gender"],
            data["preferred_gender"],
            data["bio"],
            data["photo"],
            data.get("interests", [])
        )
        await state.clear()
        await message.answer("Регистрация завершена!", reply_markup=get_main_menu_keyboard())

# Обработчик для просмотра анкет из главного меню
@dp.message(F.text == "Смотреть анкеты")
async def view_profiles(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if not await user_exists(user_id):
        await message.answer("Сначала необходимо создать анкету!", reply_markup=get_main_menu_unregistered())
        return
    candidate_id = await show_next_profile(user_id, message)
    await state.set_state(DatingStates.viewing_profiles)
    if candidate_id:
        await state.update_data(current_candidate=candidate_id)

# Обработчик для реакций при просмотре анкет – Лайк
@dp.message(DatingStates.viewing_profiles, F.text == "❤️ Лайк")
async def handle_like(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if "current_candidate" not in data:
        await message.answer("Нет анкеты для оценки.", reply_markup=get_profile_keyboard())
        return
    candidate_id = data["current_candidate"]
    user_id = message.from_user.id
    await add_reaction(user_id, candidate_id, like=True)
    
    # Если взаимный лайк:
    if await is_mutual_like(user_id, candidate_id):
        await add_match(user_id, candidate_id)
        await add_match(candidate_id, user_id)
        name_a = await get_user_name(user_id)
        name_b = await get_user_name(candidate_id)
        kb = get_main_menu_keyboard()
        print(name_a, user_id)
        chat_candidate = await bot.get_chat(candidate_id)         # получаем объект Chat
        username_candidate = chat_candidate.username
        chat_user = await bot.get_chat(user_id)           # получаем объект Chat
        username_user = chat_user.username
        # Сообщение для меня
        msg_a = f"Сосед [{name_b}](https://t.me/{username_candidate}) найден! Спишитесь с ним и продолжайте просмотр анкет, нажав кнопку ниже."
        # Сообщение для Миши
        msg_b = f"Сосед [{name_a}](https://t.me/{username_user}) найден! Спишитесь с ним и продолжайте просмотр анкет, нажав кнопку ниже."
        print(username_user, username_candidate + '    SHNCISNSNCSNSNCNSNSNS')
        await bot.send_message(user_id, msg_a, parse_mode="Markdown", reply_markup=kb)
        try:
            # Отправляем сообщение кандидату (например, Мише)
            await bot.send_message(candidate_id, msg_b, parse_mode="Markdown", reply_markup=kb)
            # Дополнительно отправляем вашу анкету кандидату
            await send_profile_to_candidate(user_id, candidate_id)
        except Exception as e:
            print(f"Не удалось отправить сообщение пользователю {candidate_id}: {e}")
    
    new_candidate = await show_next_profile(user_id, message)
    if new_candidate:
        await state.update_data(current_candidate=new_candidate)

# Обработчик для реакции "Дизлайк"
@dp.message(DatingStates.viewing_profiles, F.text == "👎 Дизлайк")
async def handle_dislike(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if "current_candidate" not in data:
        await message.answer("Нет анкеты для оценки.", reply_markup=get_profile_keyboard())
        return
    candidate_id = data["current_candidate"]
    user_id = message.from_user.id
    await add_reaction(user_id, candidate_id, like=False)
    new_candidate = await show_next_profile(user_id, message)
    if new_candidate:
        await state.update_data(current_candidate=new_candidate)

# Обработчик для реакции "Пропустить"
@dp.message(DatingStates.viewing_profiles, F.text == "➡️ Пропустить")
async def handle_skip(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    new_candidate = await show_next_profile(user_id, message)
    if new_candidate:
        await state.update_data(current_candidate=new_candidate)

# Обработчик для кнопки "Вернуться в главное меню" при просмотре анкет
@dp.message(DatingStates.viewing_profiles, F.text == "Вернуться в главное меню")
async def handle_return(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню:", reply_markup=get_main_menu_keyboard())

# Обработчик для редактирования анкеты: запускается при нажатии "Редактировать анкету"
@dp.message(F.text == "Редактировать анкету")
async def edit_profile(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    # Переводим пользователя в режим редактирования
    await state.set_state(EditProfile.waiting_for_choice)
    # Отправляем актуальную анкету с клавиатурой редактирования
    await send_full_profile(user_id, message)

# Обработчик для кнопки "Изменить имя"
@dp.message(EditProfile.waiting_for_choice, F.text == "Изменить имя")
async def edit_name(message: types.Message, state: FSMContext):
    await state.set_state(EditProfile.waiting_for_new_name)
    await message.answer("Введите новое имя:")

@dp.message(EditProfile.waiting_for_new_name)
async def process_new_name(message: types.Message, state: FSMContext):
    new_name = message.text.strip()
    user_id = message.from_user.id
    await update_user_field(user_id, "name", new_name)
    await message.answer("Имя обновлено.", reply_markup=get_edit_menu_keyboard())
    await send_full_profile(user_id, message)
    await state.set_state(EditProfile.waiting_for_choice)

# Обработчик для кнопки "Изменить возраст"
@dp.message(EditProfile.waiting_for_choice, F.text == "Изменить возраст")
async def edit_age_profile(message: types.Message, state: FSMContext):
    await state.set_state(EditProfile.waiting_for_new_age)
    await message.answer("Введите новый возраст:")

@dp.message(EditProfile.waiting_for_new_age)
async def process_new_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите корректный возраст (число).")
        return
    new_age = int(message.text)
    if new_age < 17 or new_age > 27:
        await message.answer("Наш бот подходит исключительно для молодых людей!\nДоступный возраст от 17 до 27 лет")
        await state.set_state(EditProfile.waiting_for_choice)
        await message.answer("Меню редактора анкеты:", reply_markup=get_edit_menu_keyboard())
        return
    user_id = message.from_user.id
    await update_user_field(user_id, "age", new_age)
    await message.answer("Возраст обновлён.", reply_markup=get_edit_menu_keyboard())
    await send_full_profile(user_id, message)
    await state.set_state(EditProfile.waiting_for_choice)

# Обработчик для кнопки "Изменить пол"
@dp.message(EditProfile.waiting_for_choice, F.text == "Изменить пол")
async def edit_gender_profile(message: types.Message, state: FSMContext):
    await state.set_state(EditProfile.waiting_for_new_gender)
    await message.answer("Выберите новый пол:", reply_markup=get_gender_keyboard())

@dp.message(EditProfile.waiting_for_new_gender, F.text.in_(["Я парень", "Я девушка"]))
async def process_new_gender(message: types.Message, state: FSMContext):
    if message.text == "Я парень":
        new_gender = "Мужской"
    else:
        new_gender = "Женский"
    user_id = message.from_user.id
    await update_user_field(user_id, "gender", new_gender)
    await message.answer("Пол обновлён.", reply_markup=get_edit_menu_keyboard())
    await send_full_profile(user_id, message)
    await state.set_state(EditProfile.waiting_for_choice)

@dp.message(EditProfile.waiting_for_choice, F.text == "Заполнить анкету заново")
async def reset_profile(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    # Удаляем анкету пользователя
    await delete_user_profile(user_id)
    # Сбрасываем состояние
    await state.clear()
    # Сообщаем пользователю и запускаем процесс регистрации заново
    await message.answer("Ваша анкета удалена. Давайте заполним анкету заново.", reply_markup=get_main_menu_unregistered())
    # Запускаем сценарий создания анкеты (переходим в состояние регистрации)
    await state.set_state(Registration.waiting_for_name)
    await message.answer("Как тебя зовут?", reply_markup=ReplyKeyboardRemove())


# Обработчик для кнопки "Изменить фото"
@dp.message(EditProfile.waiting_for_choice, F.text == "Изменить фото")
async def edit_photo_profile(message: types.Message, state: FSMContext):
    await state.set_state(EditProfile.waiting_for_new_photo)
    await message.answer("Пришлите новое фото:", reply_markup=ReplyKeyboardRemove())

@dp.message(EditProfile.waiting_for_new_photo, F.photo)
async def process_new_photo(message: types.Message, state: FSMContext):
    photo = message.photo[-1]
    user_id = message.from_user.id
    photo_filename = f"{user_id}_{uuid.uuid4().hex}.jpg"
    photo_path = f"{PHOTO_DIR}/{photo_filename}"
    file_info = await bot.get_file(photo.file_id)
    await bot.download_file(file_info.file_path, destination=Path(photo_path))
    await update_user_field(user_id, "photo", photo_path)
    await message.answer("Фото обновлено.", reply_markup=get_edit_menu_keyboard())
    await send_full_profile(user_id, message)
    await state.set_state(EditProfile.waiting_for_choice)

# Обработчик для кнопки "Изменить предпочитаемый пол"
@dp.message(EditProfile.waiting_for_choice, F.text == "Изменить предпочитаемый пол")
async def edit_preferred_gender_profile(message: types.Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Парня"), KeyboardButton(text="Девушку"), KeyboardButton(text="Все равно")]],
        resize_keyboard=True
    )
    await state.set_state(EditProfile.waiting_for_new_preferred_gender)
    await message.answer("Кого вы ищете?", reply_markup=kb)

@dp.message(EditProfile.waiting_for_new_preferred_gender, F.text.in_(["Парня", "Девушку", "Все равно"]))
async def process_new_preferred_gender(message: types.Message, state: FSMContext):
    pref = message.text
    if pref == "Парня":
        mapped = "Мужской"
    elif pref == "Девушку":
        mapped = "Женский"
    else:
        mapped = "Все"
    user_id = message.from_user.id
    await update_user_field(user_id, "preferred_gender", mapped)
    await message.answer("Предпочитаемый пол обновлён.", reply_markup=get_edit_menu_keyboard())
    await send_full_profile(user_id, message)
    await state.set_state(EditProfile.waiting_for_choice)


@dp.message(EditProfile.waiting_for_choice, F.text == "Изменить интересы")
async def edit_interests(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    # Сброс интересов в БД (опционально – можно и только в состоянии)
    await update_user_field(user_id, "interests", json.dumps([]))
    # Обновляем данные в состоянии: создаём пустой список для новых интересов
    await state.update_data(new_interests=[])
    # Переводим пользователя в новое состояние выбора интересов
    await state.set_state(EditProfile.waiting_for_new_interests)
    # Отправляем сообщение с клавиатурой выбора интересов
    await message.answer("Выбери до пяти интересов, которые тебе подходят:", reply_markup=get_interests_keyboard())


@dp.message(EditProfile.waiting_for_new_interests)
async def process_new_interests(message: types.Message, state: FSMContext):
    text = message.text
    # Если нажата кнопка "Завершить выбор", завершаем выбор
    if text == "Завершить выбор":
        user_data = await state.get_data()
        new_interests = user_data.get("new_interests", [])
        if not new_interests:
            await message.answer("Пожалуйста, выберите хотя бы один интерес.")
            return
            
        # Обновляем интересы в БД для пользователя
        user_id = message.from_user.id
        await update_user_field(user_id, "interests", json.dumps(new_interests))
        await state.set_state(EditProfile.waiting_for_choice)
        await message.answer("Интересы обновлены.", reply_markup=get_edit_menu_keyboard())
        await send_full_profile(user_id, message)
        return

    # Если выбран один из интересов (проверяем, что он есть в списке допустимых)
    if text in INTEREST_OPTIONS:
        user_data = await state.get_data()
        interests = user_data.get("new_interests", [])
        
        if len(interests) >= 5:
            await message.answer("Вы уже выбрали максимальное количество интересов (5). Нажмите 'Завершить выбор'.")
            return
            
        if text not in interests:
            interests.append(text)
            await state.update_data(new_interests=interests)
            await message.answer(f"Интерес '{text}' добавлен. Выбрано: {', '.join(interests)}")
            
            if len(interests) >= 5:
                user_id = message.from_user.id
                await update_user_field(user_id, "interests", json.dumps(interests))
                await state.set_state(EditProfile.waiting_for_choice)
                await message.answer("Ты выбрал максимальное количество интересов. Интересы обновлены.", reply_markup=get_edit_menu_keyboard())
                await send_full_profile(user_id, message)
        else:
            await message.answer("Этот интерес уже выбран.")
    else:
        await message.answer("Неверный выбор. Пожалуйста, выберите интерес из предложенных вариантов или нажмите 'Завершить выбор'.")


# Обработчик для кнопки "Вернуться в главное меню" (универсальный)
@dp.message(F.text == "Вернуться в главное меню")
async def return_to_main_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню:", reply_markup=get_main_menu_keyboard())

# Фолбэк-обработчик для непонятных сообщений – выводит главное меню
@dp.message()
async def fallback_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    await state.clear()
    if await user_exists(user_id):
        await message.answer("Пожалуйста, выберите опцию из меню ниже:", reply_markup=get_main_menu_keyboard())
    else:
        await message.answer("Пожалуйста, создайте анкету, чтобы пользоваться ботом.", reply_markup=get_main_menu_unregistered())

# Добавляем обработчик для кнопки "Купить премиум"
@dp.message(F.text == "Купить премиум")
async def buy_premium(message: types.Message, state: FSMContext):
    await message.answer(
        "🌟 Премиум-подписка\n\n"
        "✨ Включает:\n"
        "• 🎯 Доступ к фильтрам по возрасту\n"
        "• 🎨 Фильтрацию по интересам\n"
        "• 💫 Более точные совпадения\n"
        "• ⚡ Приоритет в поиске\n\n"
        "💰 Стоимость: 149 рублей в месяц\n\n"
        "К сожалению, функция покупки премиум-подписки пока находится в разработке.\n"
        "Следите за обновлениями!",
        reply_markup=get_edit_menu_keyboard()
    )
    await state.set_state(EditProfile.waiting_for_choice)

# Основная асинхронная функция для запуска бота
async def main():
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

# Точка входа в программу
if __name__ == "__main__":
    asyncio.run(main())