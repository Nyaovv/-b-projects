import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    ContextTypes, MessageHandler, filters
)

from config import BOT_TOKEN, WEBAPP_URL
from database import init_db, get_or_create_user, get_user_settings, update_user_settings

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start."""
    user = update.effective_user
    user_id = user.id
    
    # Создаем или получаем пользователя
    get_or_create_user(user_id)
    
    # Создаем кнопку для открытия мини-приложения
    keyboard = [
        [InlineKeyboardButton(
            "Открыть RestApp 🌙", 
            web_app=WebAppInfo(url=f"{WEBAPP_URL}")
        )]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        f"Это <b>RestApp</b> - приложение для релаксации и сна.\n\n"
        f"• Установите таймер\n"
        f"• Выберите успокаивающий звук\n"
        f"• Наслаждайтесь спокойным сном\n\n"
        f"Нажмите кнопку ниже, чтобы открыть приложение:",
        parse_mode="HTML",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help."""
    await update.message.reply_text(
        "🌙 <b>RestApp - Помощь</b>\n\n"
        "Как пользоваться приложением:\n\n"
        "1. Нажмите на кнопку «Открыть RestApp» для запуска\n"
        "2. Установите время таймера с помощью слайдера\n"
        "3. Выберите режим (выключение звука или выход)\n"
        "4. Выберите сцену с приятным звуком\n"
        "5. Нажмите «Запустить таймер»\n\n"
        "<i>Секретная функция:</i> быстро нажмите 5 раз на анимацию для активации режима дыхания 💨",
        parse_mode="HTML"
    )

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /about."""
    await update.message.reply_text(
        "🌙 <b>О приложении RestApp</b>\n\n"
        "RestApp - это приложение для релаксации и сна, помогающее расслабиться "
        "под приятные звуки природы и настроить таймер.\n\n"
        "Telegram-версия приложения создана на основе оригинального RestApp.\n\n"
        "© 2023 RestApp",
        parse_mode="HTML"
    )

async def webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка данных от мини-приложения."""
    try:
        user_id = update.effective_user.id
        data = json.loads(update.effective_message.web_app_data.data)
        
        # Обновляем настройки пользователя
        update_user_settings(user_id, data)
        
        await update.message.reply_text(
            "✅ Ваши настройки сохранены!",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error processing webapp data: {e}")
        await update.message.reply_text("❌ Произошла ошибка при обработке данных")

def main():
    """Запуск бота."""
    # Инициализация БД
    init_db()
    
    # Создание приложения
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, webapp_data))
    
    # Запуск бота
    application.run_polling()

if __name__ == "__main__":
    main()
