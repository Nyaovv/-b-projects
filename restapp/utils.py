"""Вспомогательные функции для таймера и UI."""

def seconds_to_slider(seconds: int, max_time: int) -> int:
    """Преобразует секунды в значение слайдера."""
    return int((seconds / max_time) * 1000)

def slider_to_seconds(value: int, max_time: int) -> int:
    """Преобразует значение слайдера в секунды."""
    return max(60, int((value / 1000) * max_time))