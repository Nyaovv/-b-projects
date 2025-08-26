"""Модуль для аудио-констант и инициализации."""

import pygame

pygame.mixer.init()
pygame.mixer.set_num_channels(32)  # Чтобы клики могли накладываться

MEDIA = {
    "Белый шум": ("white_noise.ogg", "white_noise.gif", "white_noise.png", "click.ogg"),
    "Камин": ("fire.ogg", "fire.gif", "fire.png", "crack.ogg"),
    "Дождь": ("rain.ogg", "rain.gif", "rain.png", "drop.ogg"),
}

BREATH_CLICK = "breath.ogg"  # Отдельный клик для режима дыхания