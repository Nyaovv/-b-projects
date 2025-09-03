"""Модуль для аудио-констант и инициализации."""
import os
import pygame
from PyQt5 import QtWidgets

pygame.mixer.init()
pygame.mixer.set_num_channels(32)  # Чтобы клики могли накладываться

MEDIA = {
    "Белый шум": ("white_noise.ogg", "white_noise.gif", "white_noise.png", "click.ogg"),
    "Камин": ("fire.ogg", "fire.gif", "fire.png", "crack.ogg"),
    "Дождь": ("rain.ogg", "rain.gif", "rain.png", "drop.ogg"),
}

BREATH_CLICK = os.path.join(os.path.dirname(os.path.dirname(__file__)), "media", "breath_tap.ogg") # Отдельный клик для режима дыхания
