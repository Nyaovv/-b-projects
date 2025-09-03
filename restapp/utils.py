import os

"""Вспомогательные функции для таймера и UI."""

def seconds_to_slider(seconds: int, max_time: int) -> int:
    """Преобразует секунды в значение слайдера."""
    return int((seconds / max_time) * 1000)

def slider_to_seconds(value: int, max_time: int) -> int:
    """Преобразует значение слайдера в секунды."""
    return max(60, int((value / 1000) * max_time))

def discover_scenes(scenes_dir):
    """Находит все папки-сцены и их медиафайлы."""
    scenes = {}
    if not os.path.isdir(scenes_dir):
        return scenes

    for scene_name in os.listdir(scenes_dir):
        scene_path = os.path.join(scenes_dir, scene_name)
        if os.path.isdir(scene_path):
            files = os.listdir(scene_path)
            png = next((f for f in files if f.endswith('.png')), None)
            gif = next((f for f in files if f.endswith('.gif')), None)
            ogg = next((f for f in files if f.endswith('.ogg') and 'tap' not in f), None)
            tap_ogg = next((f for f in files if f.endswith('tap.ogg')), None)
            if png and gif and ogg:
                scenes[scene_name] = {
                    'png': os.path.join(scene_path, png),
                    'gif': os.path.join(scene_path, gif),
                    'ogg': os.path.join(scene_path, ogg),
                    'tap_ogg': os.path.join(scene_path, tap_ogg) if tap_ogg else None
                }
    return scenes