import asyncio
import logging
import sqlite3

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import BOT_TOKEN


logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

DB_NAME = "career_compass.db"
waiting_for = {}
test_data = {}


def db():
    return sqlite3.connect(DB_NAME)


def create_database():
    connection = db()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            age INTEGER,
            interests TEXT DEFAULT '',
            skills TEXT DEFAULT '',
            goal TEXT DEFAULT ''
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS careers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            tags TEXT NOT NULL,
            first_step TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            career_id INTEGER,
            score INTEGER
        )
    """)

    careers = [
        ("Программист", "Создаёт сайты, приложения и программы.",
         "programming,computer,technology,math,logic",
         "Начать с Python и сделать небольшой проект."),
        ("Game Developer", "Создаёт компьютерные игры и игровую механику.",
         "programming,computer,games,unity,unreal",
         "Попробовать Roblox Studio или Unity."),
        ("UX/UI дизайнер", "Проектирует внешний вид приложений и сайтов.",
         "design,art,creative,figma,computer",
         "Изучить Figma и сделать дизайн приложения."),
        ("Видеомонтажёр", "Монтирует видео для YouTube, рекламы и социальных сетей.",
         "video,editing,creative,youtube,music",
         "Смонтировать короткое видео в DaVinci Resolve."),
        ("3D-художник", "Создаёт 3D-модели и виртуальные объекты.",
         "3d,art,creative,games,design,blender",
         "Попробовать Blender и создать первую модель."),
        ("Аналитик данных", "Работает с данными и ищет закономерности.",
         "data,math,logic,programming,excel,sql",
         "Изучить Excel, SQL и основы анализа данных."),
        ("SMM-специалист", "Развивает социальные сети и создаёт контент.",
         "social,content,video,creative,marketing",
         "Попробовать вести тематический аккаунт."),
        ("Графический дизайнер", "Создаёт логотипы, постеры и баннеры.",
         "design,art,creative,photoshop,figma",
         "Создать несколько постеров или логотипов."),
        ("Робототехник", "Создаёт и программирует роботов.",
         "robotics,programming,technology,math,engineering",
         "Познакомиться с Arduino."),
        ("Предприниматель", "Создаёт проекты, продукты и развивает бизнес.",
         "business,marketing,communication,creative,leadership",
         "Придумать небольшой проект и проблему, которую он решает.")
    ]

    cursor.execute("SELECT COUNT(*) FROM careers")

    if cursor.fetchone()[0] == 0:
        cursor.executemany("""
            INSERT INTO careers (name, description, tags, first_step)
            VALUES (?, ?, ?, ?)
        """, careers)

    connection.commit()
    connection.close()


def create_user(user_id, name):
    connection = db()
    cursor = connection.cursor()

    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, name) VALUES (?, ?)",
        (user_id, name)
    )

    connection.commit()
    connection.close()


def get_user(user_id):
    connection = db()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    connection.close()
    return user


def update_user(user_id, field, value):
    fields = {"name", "age", "interests", "skills", "goal"}

    if field not in fields:
        return

    connection = db()
    cursor = connection.cursor()
    cursor.execute(
        f"UPDATE users SET {field} = ? WHERE user_id = ?",
        (value, user_id)
    )
    connection.commit()
    connection.close()


def get_careers():
    connection = db()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM careers")
    careers = cursor.fetchall()
    connection.close()
    return careers


def get_career(career_id):
    connection = db()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM careers WHERE id = ?", (career_id,))
    career = cursor.fetchone()
    connection.close()
    return career


def save_recommendation(user_id, career_id, score):
    connection = db()
    cursor = connection.cursor()

    cursor.execute(
        "INSERT INTO recommendations (user_id, career_id, score) VALUES (?, ?, ?)",
        (user_id, career_id, score)
    )

    connection.commit()
    connection.close()


KEYWORDS = {
    "programming": ["программ", "код", "python", "javascript", "java", "разработ"],
    "computer": ["компьютер", "пк", "технолог", "it", "техника"],
    "games": ["игр", "гейм", "roblox", "minecraft", "unity", "unreal"],
    "design": ["дизайн", "figma", "интерфейс", "визуал"],
    "art": ["рисован", "рисую", "арт", "худож", "творч"],
    "video": ["видео", "монтаж", "youtube", "ролик"],
    "creative": ["творч", "креатив", "создавать", "придумывать"],
    "math": ["математ", "матем", "цифр", "формул"],
    "data": ["данн", "аналит", "статист"],
    "business": ["бизнес", "стартап", "предприним", "деньги"],
    "marketing": ["маркет", "реклам", "продаж"],
    "social": ["соцсет", "instagram", "tiktok", "контент"],
    "3d": ["3d", "трехмер", "трёхмер", "blender", "модел"],
    "robotics": ["робот", "arduino", "механик"],
    "communication": ["общен", "люд", "разговор"],
    "leadership": ["лидер", "руковод", "команд"],
    "logic": ["логик", "задач", "головолом"]
}


def find_categories(text):
    text = text.lower()
    result = []

    for category, words in KEYWORDS.items():
        if any(word in text for word in words):
            result.append(category)

    return result


def get_recommendations(user_id):
    user = get_user(user_id)

    if not user:
        return []

    text = " ".join([
        user[3] or "",
        user[4] or "",
        user[5] or ""
    ])

    categories = set(find_categories(text))
    results = []

    for career in get_careers():
        tags = set(career[3].split(","))
        score = len(categories & tags)

        if score:
            results.append((career, score))

    results.sort(key=lambda item: item[1], reverse=True)
    return results[:3]


def main_menu():
    builder = InlineKeyboardBuilder()

    buttons = [
        ("🧭 Подобрать профессию", "recommend"),
        ("🧠 Мини-тест", "test"),
        ("👤 Мой профиль", "profile"),
        ("✏️ Изменить интересы", "edit"),
        ("💼 Все профессии", "careers"),
        ("💡 Как это работает", "about")
    ]

    for text, callback in buttons:
        builder.button(text=text, callback_data=callback)

    builder.adjust(1)
    return builder.as_markup()


def career_keyboard(career_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="📖 Подробнее", callback_data=f"career:{career_id}")
    builder.button(text="🔙 В меню", callback_data="menu")
    builder.adjust(1)
    return builder.as_markup()


def test_keyboard(question):
    builder = InlineKeyboardBuilder()

    options = {
        1: [
            ("💻 Технологии", "test:technology"),
            ("🎨 Творчество", "test:creative"),
            ("📊 Анализ", "test:analysis"),
            ("💼 Бизнес", "test:business")
        ],
        2: [
            ("🎮 Игры", "test:games"),
            ("🎥 Видео", "test:video"),
            ("🤖 Роботы", "test:robotics"),
            ("📱 Соцсети", "test:social")
        ],
        3: [
            ("💻 Компьютер", "test:computer"),
            ("👥 Люди", "test:people"),
            ("🎨 Создавать", "test:creative"),
            ("📈 Анализировать", "test:analysis")
        ]
    }

    for text, callback in options[question]:
        builder.button(text=text, callback_data=callback)

    builder.adjust(1)
    return builder.as_markup()


def profile_text(user):
    return (
        "👤 Твой профиль\n\n"
        f"Имя: {user[1] or 'Не указано'}\n"
        f"Возраст: {user[2] or 'Не указано'}\n"
        f"Интересы: {user[3] or 'Не указано'}\n"
        f"Навыки: {user[4] or 'Не указано'}\n"
        f"Цель: {user[5] or 'Не указано'}"
    )


def recommendation_text(career, score):
    return (
        f"🎯 {career[1]}\n\n"
        f"{career[2]}\n\n"
        f"Совпадений с твоим профилем: {score}\n\n"
        f"🚀 Первый шаг:\n{career[4]}"
    )


@dp.message(Command("start"))
async def start(message: Message):
    create_user(message.from_user.id, message.from_user.first_name)

    await message.answer(
        "👋 Привет! Я Career Compass.\n\n"
        "Я помогу подобрать профессии на основе твоих интересов, "
        "навыков и целей.\n\n"
        "Можешь пройти мини-тест или заполнить профиль.",
        reply_markup=main_menu()
    )


@dp.message(Command("menu"))
async def menu_command(message: Message):
    await message.answer("📋 Главное меню:", reply_markup=main_menu())


@dp.callback_query(F.data == "menu")
async def menu_callback(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("📋 Главное меню:", reply_markup=main_menu())


@dp.callback_query(F.data == "about")
async def about_callback(callback: CallbackQuery):
    await callback.answer()

    await callback.message.answer(
        "💡 Как работает Career Compass?\n\n"
        "1. Ты рассказываешь о своих интересах и навыках.\n"
        "2. Бот анализирует ключевые слова.\n"
        "3. Профессии получают баллы за совпадения.\n"
        "4. Бот показывает наиболее подходящие варианты.\n\n"
        "Базу профессий можно расширять новыми записями.",
        reply_markup=main_menu()
    )


@dp.callback_query(F.data == "profile")
async def profile_callback(callback: CallbackQuery):
    await callback.answer()

    user = get_user(callback.from_user.id)

    if user:
        await callback.message.answer(
            profile_text(user),
            reply_markup=main_menu()
        )


@dp.callback_query(F.data == "edit")
async def edit_callback(callback: CallbackQuery):
    await callback.answer()
    waiting_for[callback.from_user.id] = "interests"

    await callback.message.answer(
        "✏️ Напиши свои интересы одним сообщением.\n\n"
        "Например:\n"
        "игры, компьютеры, программирование, видео"
    )


@dp.callback_query(F.data == "recommend")
async def recommend_callback(callback: CallbackQuery):
    await callback.answer()

    results = get_recommendations(callback.from_user.id)

    if not results:
        await callback.message.answer(
            "🤔 Мне пока не хватает информации.\n\n"
            "Напиши свои интересы через «✏️ Изменить интересы» "
            "или пройди «🧠 Мини-тест».",
            reply_markup=main_menu()
        )
        return

    await callback.message.answer("🎯 Вот подходящие направления:")

    for career, score in results:
        save_recommendation(callback.from_user.id, career[0], score)

        await callback.message.answer(
            recommendation_text(career, score),
            reply_markup=career_keyboard(career[0])
        )


@dp.callback_query(F.data == "careers")
async def careers_callback(callback: CallbackQuery):
    await callback.answer()

    text = "💼 Профессии в базе:\n\n"

    for career in get_careers():
        text += f"• {career[1]}\n"

    await callback.message.answer(text, reply_markup=main_menu())


@dp.callback_query(F.data.startswith("career:"))
async def career_details(callback: CallbackQuery):
    await callback.answer()

    try:
        career_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.message.answer("Не удалось найти профессию.")
        return

    career = get_career(career_id)

    if not career:
        await callback.message.answer("Профессия не найдена.")
        return

    await callback.message.answer(
        f"💼 {career[1]}\n\n"
        f"{career[2]}\n\n"
        f"🚀 С чего начать:\n{career[4]}",
        reply_markup=main_menu()
    )


@dp.callback_query(F.data == "test")
async def test_callback(callback: CallbackQuery):
    await callback.answer()

    test_data[callback.from_user.id] = {
        "answers": [],
        "question": 1
    }

    await callback.message.answer(
        "🧠 Мини-тест\n\nЧто тебе интереснее?",
        reply_markup=test_keyboard(1)
    )


@dp.callback_query(F.data.startswith("test:"))
async def test_answer(callback: CallbackQuery):
    await callback.answer()

    user_id = callback.from_user.id
    answer = callback.data.split(":")[1]

    data = test_data.setdefault(
        user_id,
        {"answers": [], "question": 1}
    )

    data["answers"].append(answer)
    data["question"] += 1

    if data["question"] <= 3:
        questions = {
            2: "Что из этого тебе ближе?",
            3: "Какой формат работы тебе интереснее?"
        }

        await callback.message.answer(
            questions[data["question"]],
            reply_markup=test_keyboard(data["question"])
        )
        return

    categories = []

    mapping = {
        "technology": ["programming", "computer"],
        "creative": ["design", "creative"],
        "analysis": ["data", "math", "logic"],
        "business": ["business", "marketing"],
        "games": ["games", "programming"],
        "video": ["video", "creative"],
        "robotics": ["robotics", "programming"],
        "social": ["social", "marketing"],
        "computer": ["computer"],
        "people": ["communication"]
    }

    for answer in data["answers"]:
        categories.extend(mapping.get(answer, []))

    update_user(
        user_id,
        "interests",
        ", ".join(categories)
    )

    del test_data[user_id]

    await callback.message.answer(
        "✅ Тест завершён!\n\n"
        "Я сохранил результат. Теперь можно подобрать профессии.",
        reply_markup=main_menu()
    )


@dp.message()
async def text_message(message: Message):
    user_id = message.from_user.id
    text = message.text.strip()

    if not text:
        return

    create_user(user_id, message.from_user.first_name)

    if user_id in waiting_for:
        update_user(user_id, waiting_for[user_id], text)
        del waiting_for[user_id]

        await message.answer(
            "✅ Информация сохранена!",
            reply_markup=main_menu()
        )
        return

    update_user(user_id, "interests", text)

    await message.answer(
        "Я сохранил это как твои интересы.\n\n"
        "Теперь нажми «🧭 Подобрать профессию».",
        reply_markup=main_menu()
    )


async def main():
    create_database()
    print("Career Compass запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
