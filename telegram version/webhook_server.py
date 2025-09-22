import os
import json
import logging
from flask import Flask, request, jsonify, send_from_directory
from config import DATABASE_URL
from database import get_user_settings, update_user_settings

app = Flask(__name__, static_folder='webapp')
logging.basicConfig(level=logging.INFO)

@app.route('/')
def index():
    """Корневой маршрут, отдает основной файл приложения."""
    return send_from_directory('webapp', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Обслуживание статических файлов."""
    return send_from_directory('webapp', path)

@app.route('/media/<path:path>')
def serve_media(path):
    """Обслуживание медиафайлов."""
    return send_from_directory('media', path)

@app.route('/api/settings/<int:user_id>', methods=['GET'])
def get_settings(user_id):
    """API для получения настроек пользователя."""
    try:
        settings = get_user_settings(user_id)
        return jsonify({"success": True, "settings": settings})
    except Exception as e:
        logging.error(f"Error getting settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/settings/<int:user_id>', methods=['POST'])
def save_settings(user_id):
    """API для сохранения настроек пользователя."""
    try:
        data = request.json
        update_user_settings(user_id, data)
        return jsonify({"success": True})
    except Exception as e:
        logging.error(f"Error saving settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
