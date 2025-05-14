import logging
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    ChatMemberHandler,
    MessageHandler,
    CommandHandler,
    filters
)
import sqlite3

# === Загрузка переменных окружения ===
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID"))

# === Логирование ===
logging.basicConfig(level=logging.INFO)

# === Подключение к БД ===
def get_db_connection():
    return sqlite3.connect('employees.db')

def is_employee(phone):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM employees WHERE phone_number=?", (phone,))
    result = cur.fetchone()
    conn.close()
    return result is not None

def add_employee_to_db(name, phone):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO employees (name, phone_number) VALUES (?, ?)", (name, phone))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

# === Обработчик новых участников ===
async def handle_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_member: Update.chat_member = update.my_chat_member

    if chat_member.chat.id != GROUP_ID:
        return

    user = chat_member.new_chat_member.user

    if chat_member.new_chat_member.status == "member":
        logging.info(f"Новый участник: {user.full_name} ({user.id})")

        try:
            await context.bot.send_message(
                chat_id=user.id,
                text="Добро пожаловать! Чтобы получить доступ к группе, отправьте свой контактный номер телефона."
            )
        except Exception as e:
            logging.warning(f"Не могу отправить ЛС пользователю {user.id}: {e}. Возможно, он не запускал бота.")

# === Получение контакта от пользователя ===
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    contact = update.message.contact

    if contact and contact.user_id == user.id:
        phone = contact.phone_number
        logging.info(f"Получен номер: {phone} от {user.id}")

        if is_employee(phone):
            await update.message.reply_text("✅ Вы успешно авторизованы и можете оставаться в группе.")
        else:
            await update.message.reply_text("❌ Ваш номер не найден в списке сотрудников.")
            try:
                await context.bot.ban_chat_member(chat_id=GROUP_ID, user_id=user.id)
                await update.message.reply_text("Вы были удалены из группы")