import os
from pathlib import Path

# Базовые пути
BASE_DIR = Path(__file__).resolve().parent
MEDIA_DIR = os.path.join(BASE_DIR, 'media')
SCENES_DIR = os.path.join(MEDIA_DIR, 'scenes')

# Токен для Telegram бота
BOT_TOKEN = "8288832511:AAHofkk-sifm1LK2FK4ap7C64UEf6HSXh54"

# Настройки для базы данных
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'restapp.db')}"

# URL для веб-приложения (нужно заменить на ваш хостинг при деплое)
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-web-app-url.com")

# Настройки таймера по умолчанию
DEFAULT_SETTINGS = {
    "volume": 50,       # Громкость (0-100)
    "timer": 90,        # Минуты таймера
    "scene": "fire",    # Сцена по умолчанию
    "mode": "mute"      # Действие по окончании (mute/exit)
}

# Настройки для режима дыхания
BREATHING_SETTINGS = {
    "inhale_time": 4.0,
    "hold_time": 4.0,
    "exhale_time": 4.0,
    "rest_time": 4.0
}

# Сцены с медиафайлами
SCENES = {
    "fire": {
        "name": "Камин",
        "sound": "fire.ogg",
        "animation": "fire.gif", 
        "thumbnail": "fire.png",
        "tap_sound": "crack.ogg"
    },
    "rain": {
        "name": "Дождь",
        "sound": "rain.ogg",
        "animation": "rain.gif",
        "thumbnail": "rain.png",
        "tap_sound": "drop.ogg"
    },
    "white_noise": {
        "name": "Белый шум",
        "sound": "white_noise.ogg",
        "animation": "white_noise.gif",
        "thumbnail": "white_noise.png",
        "tap_sound": "click.ogg"
    }
}
