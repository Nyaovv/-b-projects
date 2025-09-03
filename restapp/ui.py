"""Модуль с UI-классами для RestApp (исправленная версия).
   Заменяй весь файл restapp/ui.py на этот.
"""

import os
import time
import ctypes
import math
import random

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QStyleOptionSlider, QStyle

import pygame

from .audio import MEDIA, BREATH_CLICK
from .utils import seconds_to_slider, slider_to_seconds, discover_scenes

SCENES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'media', 'scenes')
SCENES = discover_scenes(SCENES_DIR)

# ------------------------------------------------------------------
# Виджеты
# ------------------------------------------------------------------

class TickLabels(QtWidgets.QWidget):
    """Кастомный виджет для меток под слайдером."""

    def __init__(self, slider: QtWidgets.QSlider, marks_minutes: list[int], max_minutes: int):
        super().__init__()
        self.slider = slider
        self.marks = marks_minutes
        self.max_minutes = max_minutes
        self.setFixedHeight(24)

    def paintEvent(self, e: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        pen = QtGui.QPen(QtGui.QColor("#CCCCCC"))
        painter.setPen(pen)

        opt = QStyleOptionSlider()
        opt.initFrom(self.slider)
        opt.orientation = QtCore.Qt.Horizontal
        opt.minimum = self.slider.minimum()
        opt.maximum = self.slider.maximum()
        opt.sliderPosition = self.slider.value()
        groove = self.slider.style().subControlRect(
            QStyle.CC_Slider, opt, QStyle.SC_SliderGroove, self.slider
        )

        left = groove.left()
        width = groove.width()
        baseline = self.height() - 6

        for m in self.marks:
            frac = m / self.max_minutes
            x = left + int(frac * width)
            text = str(m)
            # Специальные подправки для читаемости
            if m == 10:
                x += 6
            if m == 240:
                x -= 12
            tw = painter.fontMetrics().horizontalAdvance(text)
            painter.drawText(x - tw // 2, baseline, text)


class ClickableLabel(QtWidgets.QLabel):
    """Кликабельная метка для GIF."""

    clicked = QtCore.pyqtSignal()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        self.clicked.emit()
        super().mousePressEvent(event)


class MovieScaler(QtCore.QObject):
    """Объект для плавного масштабирования QMovie."""

    def __init__(self, label: QtWidgets.QLabel, base_size: QtCore.QSize = QtCore.QSize(240, 240)):
        super().__init__()
        self._scale = 1.0
        self.label = label
        self.base_size = base_size

    @QtCore.pyqtProperty(float)
    def scale(self) -> float:
        return self._scale

    @scale.setter
    def scale(self, value: float) -> None:
        self._scale = float(value)
        movie = self.label.movie()
        if movie:
            w = max(1, int(self.base_size.width() * self._scale))
            h = max(1, int(self.base_size.height() * self._scale))
            movie.setScaledSize(QtCore.QSize(w, h))

class GifOverlayAnimator(QtWidgets.QWidget):
    """Аниматор поверх GIF для плавного скейла и рандомного движения."""

    def __init__(self, target_label: QtWidgets.QLabel, base_size: QtCore.QSize = QtCore.QSize(240, 240)):
        super().__init__(target_label.parent())
        self.label = target_label
        self.base_size = base_size
        self._scale = 1.0
        self._offset = QtCore.QPointF(0, 0)
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(16)  # ~60 FPS
        self.timer.timeout.connect(self.update_animation)
        self.phase = 0.0
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.hide()
        self.setGeometry(self.label.geometry())
        self.raise_()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        self.label.clicked.emit()
        super().mousePressEvent(event)

    def start_bounce(self):
        self.phase = 0.0
        self.label.hide()
        self.show()
        self.raise_()
        self.timer.start()

    def stop_bounce(self):
        self.timer.stop()
        self.label.show()
        self.hide()

    def update_animation(self):
        self.phase += 0.08
        self._scale = 1.0 + math.sin(self.phase) * 0.1  # подпрыгивает до ±10%
        dx = math.sin(self.phase * 1.5) * 3
        dy = math.cos(self.phase * 1.3) * 3
        self._offset = QtCore.QPointF(dx, dy)
        self.update()

        # через 1.2 сек остановить
        if self.phase > math.pi * 2:
            self.stop_bounce()

    def paintEvent(self, e: QtGui.QPaintEvent) -> None:
        if not self.label.movie():
            return
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        movie = self.label.movie()
        frame = movie.currentPixmap()
        if frame.isNull():
            return

        w = int(self.base_size.width() * self._scale)
        h = int(self.base_size.height() * self._scale)
        x = (self.width() - w) // 2 + int(self._offset.x())
        y = (self.height() - h) // 2 + int(self._offset.y())

        painter.drawPixmap(x, y, w, h, frame)


# ------------------------------------------------------------------
# Оверлей дыхания (упрощённый, но с заглушками intro/outro)
# ------------------------------------------------------------------

class BreathingOverlay(QtWidgets.QWidget):
    """Оверлей для дыхательной анимации 4-4-4-4 (рисуется в paintEvent)."""

    def __init__(self, parent: QtWidgets.QWidget = None, on_click: callable = None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("background: transparent;")

        self._on_click = on_click

        # цикл дыхания
        self.t_in = 4.0
        self.t_hold1 = 4.0
        self.t_out = 4.0
        self.t_hold2 = 4.0
        self.cycle = self.t_in + self.t_hold1 + self.t_out + self.t_hold2

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self.update)
        self._elapsed = QtCore.QElapsedTimer()

        # кнопка возврата (в угле)
        self.btn_exit = QtWidgets.QPushButton("←", self)
        self.btn_exit.setToolTip("Вернуться к обычному режиму")
        self.btn_exit.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_exit.setStyleSheet("""
            QPushButton {
                font-size: 20pt; font-weight: bold; color: #fff;
                background: #D32F2F; border: none; border-radius: 20px;
                padding: 8px 12px; box-shadow: 0 2px 8px #0008;
            }
            QPushButton:hover { background: #B71C1C; }
        """)
        # при нажатии вызываем плавное исчезновение, если вызывают play_outro, то он и закроет
        self.btn_exit.clicked.connect(lambda: self.play_outro(self.hide))

        # частицы (маленькие шарики)
        self.particles = []
        for _ in range(10):
            self.particles.append({
                'pos': QtCore.QPointF(0, 0),
                'vel': QtCore.QPointF(0, 0),
                'radius': 5 + random.random() * 10,
                'phase': random.random() * 2 * math.pi
            })

        # --- добавьте для баунса ---
        self._bounce_phase = 0.0
        self._bounce_scale = 1.0
        self._bounce_timer = QtCore.QTimer(self)
        self._bounce_timer.setInterval(16)
        self._bounce_timer.timeout.connect(self.update_bounce)

    # Заглушки intro/outro (на случай, если код в SleepTimer вызывает их)
    def play_intro(self, finished_callback=None):
        self.show()
        self.raise_()
        self._elapsed.start()
        self._timer.start()
        if callable(finished_callback):
            finished_callback()

    def play_outro(self, finished_callback=None):
        self._timer.stop()
        self.hide()
        if callable(finished_callback):
            finished_callback()

    def showEvent(self, e: QtGui.QShowEvent) -> None:
        self._elapsed.start()
        self._timer.start()
        self.update()
        super().showEvent(e)

    def hideEvent(self, e: QtGui.QHideEvent) -> None:
        self._timer.stop()
        super().hideEvent(e)

    def resizeEvent(self, e: QtGui.QResizeEvent) -> None:
        margin = 16
        btn_size = self.btn_exit.sizeHint()
        self.btn_exit.setFixedSize(btn_size)
        # Кнопка справа внутри overlay
        self.btn_exit.move(self.width() - btn_size.width() - margin, margin)
        super().resizeEvent(e)

    def start_bounce(self):
        self._bounce_phase = 0.0
        self._bounce_timer.start()

    def update_bounce(self):
        self._bounce_phase += 0.16  # Было 0.08, теперь быстрее
        self._bounce_scale = 1.0 + math.sin(self._bounce_phase) * 0.04  # Было 0.1, теперь слабее
        self.update()
        if self._bounce_phase > math.pi * 2:
            self._bounce_timer.stop()
            self._bounce_scale = 1.0

    def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
        if callable(self._on_click):
            try:
                self._on_click()
            except Exception:
                pass
        self.start_bounce()  # <-- добавьте вызов баунса
        super().mousePressEvent(e)

    def keyPressEvent(self, e: QtGui.QKeyEvent) -> None:
        if e.key() == QtCore.Qt.Key_Escape:
            self.play_outro(self.hide)
        super().keyPressEvent(e)

    def _radius_for_time(self, t_norm: float, base: float, amp: float) -> float:
        # та же кривая, что и раньше
        t = t_norm % self.cycle
        if t < self.t_in:
            k = t / self.t_in
            return base + amp * k
        t -= self.t_in
        if t < self.t_hold1:
            return base + amp
        t -= self.t_hold1
        if t < self.t_out:
            k = 1.0 - (t / self.t_out)
            return base + amp * k
        return base

    def set_gif_geometry(self, gif_rect):
        self._gif_rect = gif_rect

    def paintEvent(self, e: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # Центр шара — по центру гифки, независимо от overlay
        if hasattr(self, "_gif_rect") and self._gif_rect:
            gif_rect = self._gif_rect
            center = QtCore.QPoint(gif_rect.x() + gif_rect.width() // 2, gif_rect.y() + gif_rect.height() // 2)
            min_side = min(gif_rect.width(), gif_rect.height())
        else:
            rect = self.rect()
            center = rect.center()
            min_side = min(rect.width(), rect.height())

        base = 0.20 * min_side
        amp = 0.30 * min_side

        t = (self._elapsed.elapsed() / 1000.0) if self._elapsed.isValid() else 0.0
        t = t % self.cycle
        radius = self._radius_for_time(t, base, amp)

        # --- применяем bounce scale ---
        radius *= getattr(self, "_bounce_scale", 1.0)

        alpha_factor = 1.0
        phase = t
        if phase >= self.t_in + self.t_hold1 and phase < self.t_in + self.t_hold1 + self.t_out:
            elapsed_out = phase - (self.t_in + self.t_hold1)
            alpha_factor = 1.0 - (elapsed_out / self.t_out) * 0.5

        grad = QtGui.QRadialGradient(center, radius)
        color = QtGui.QColor(144, 202, 249, int(140 * alpha_factor))
        center_color = QtGui.QColor(144, 202, 249, int(70 * alpha_factor))
        grad.setColorAt(0.0, center_color)
        grad.setColorAt(1.0, color)

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QBrush(grad))
        painter.drawEllipse(center, int(radius), int(radius))

        scale_factor = radius / (base + amp / 2)
        for p in self.particles:
            p['phase'] += 0.05
            offset_x = math.sin(p['phase']) * (radius * 0.4)
            offset_y = math.cos(p['phase']) * (radius * 0.4)
            p['pos'] = QtCore.QPointF(offset_x * scale_factor, offset_y * scale_factor)

            p_grad = QtGui.QRadialGradient(center + p['pos'], p['radius'])
            p_color = QtGui.QColor(173, 216, 230, int(100 * alpha_factor))
            p_center_color = QtGui.QColor(173, 216, 230, int(50 * alpha_factor))
            p_grad.setColorAt(0.0, p_center_color)
            p_grad.setColorAt(1.0, p_color)
            painter.setBrush(QtGui.QBrush(p_grad))
            painter.drawEllipse(center + p['pos'], int(p['radius']), int(p['radius']))


# ------------------------------------------------------------------
# Мелкие элементы
# ------------------------------------------------------------------

class SelectableButton(QtWidgets.QPushButton):
    """Выбираемая кнопка для режимов."""

    def __init__(self, text: str, icon: str = None):
        super().__init__(text)
        self.setCheckable(True)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        if icon:
            self.setIcon(QtGui.QIcon(icon))
            self.setIconSize(QtCore.QSize(32, 32))
        self.setStyleSheet("""
            QPushButton {
                border: 2px solid #555;
                border-radius: 12px;
                padding: 12px;
                background: #2E2E2E;
                font-weight: 600;
                color: #CCCCCC;
            }
            QPushButton:checked {
                border: 2px solid #90CAF9;
                background: #424242;
                color: #FFFFFF;
            }
        """)


# ------------------------------------------------------------------
# Главное окно
# ------------------------------------------------------------------

class SleepTimer(QtWidgets.QWidget):
    """Основное окно приложения."""

    def __init__(self):
        super().__init__()
        self.current_effect = None
        self.setWindowTitle("Таймер сна 💤")
        self.setGeometry(200, 200, 700, 600)

        self.setStyleSheet(
            """
            QWidget { background-color: #1E1E1E; color: #CCCCCC; font-family: Segoe UI, sans-serif; font-size: 12pt; }
            QLabel { color: #CCCCCC; }
            QSlider::groove:horizontal { border: 1px solid #444; height: 6px; background: #333; }
            QSlider::handle:horizontal { background: #90CAF9; border: 1px solid #5A9BD5; width: 16px; margin: -5px 0; border-radius: 8px; }
            """
        )

        self.settings = QtCore.QSettings("RestApp", "SleepTimer")

        root = QtWidgets.QVBoxLayout(self)

        # Время и слайдер
        self.label_time = QtWidgets.QLabel()
        root.addWidget(self.label_time)

        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(1000)
        self.slider.sliderReleased.connect(self.on_slider_released)
        root.addWidget(self.slider)

        self.marks_minutes = [1, 10, 30, 60, 90, 120, 150, 180, 210, 240]
        self.max_minutes = 240
        root.addWidget(TickLabels(self.slider, self.marks_minutes, self.max_minutes))

        # Режимы (кнопки)
        mode_layout = QtWidgets.QHBoxLayout()
        self.btn_mute = SelectableButton("Выключить звук 🔇")
        self.btn_shutdown = SelectableButton("Выключить ноут 💀")
        mode_layout.addWidget(self.btn_mute)
        mode_layout.addWidget(self.btn_shutdown)
        root.addLayout(mode_layout)

        self.mode_group = QtWidgets.QButtonGroup(self)
        self.mode_group.addButton(self.btn_mute)
        self.mode_group.addButton(self.btn_shutdown)
        self.btn_mute.setChecked(True)

        # Громкость
        self.label_vol = QtWidgets.QLabel()
        root.addWidget(self.label_vol)

        self.slider_vol = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_vol.setMinimum(0)
        self.slider_vol.setMaximum(100)
        vol_is_zero = self.settings.value("vol_is_zero", False, type=bool)
        self.slider_vol.setValue(0 if vol_is_zero else 20)
        self.slider_vol.valueChanged.connect(self.change_volume)
        root.addWidget(self.slider_vol)
        self.change_volume(self.slider_vol.value())

        # Кнопка старта (единственная кнопка, потом меняет текст)
        self.btn_action = QtWidgets.QPushButton("Запустить таймер 🚀")
        self.btn_action.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_action.clicked.connect(self.on_action_button)
        self.btn_action.setStyleSheet(
            "padding: 10px 16px; border-radius: 10px; border: 1px solid #666; background: #2E2E2E; font-weight: 600; color: #DDDDDD;"
        )
        root.addWidget(self.btn_action)

        # GIF container
        self.gif_container = QtWidgets.QWidget()
        self.gif_container.setFixedSize(240, 240)
        root.addWidget(self.gif_container, alignment=QtCore.Qt.AlignCenter)

        # GIF
        self.gif_label = ClickableLabel(self.gif_container, alignment=QtCore.Qt.AlignCenter)
        self.gif_label.setGeometry(0, 0, 240, 240)

        # Аниматор для GIF (поверх, вместо QPropertyAnimation)
        self.gif_animator = GifOverlayAnimator(self.gif_label, QtCore.QSize(240, 240))
        self.gif_animator.setGeometry(0, 0, 240, 240)

        self.gif_label.clicked.connect(self.on_gif_clicked)

        # Кнопки-превью звуков
        sound_layout = QtWidgets.QHBoxLayout()
        self.sound_buttons = {}
        for name, files in SCENES.items():
            btn = SelectableButton("", files['png'])
            btn.setIcon(QtGui.QIcon(files['png']))
            btn.setIconSize(QtCore.QSize(96, 96))
            btn.clicked.connect(lambda _, n=name: self.on_scene_change(n))
            sound_layout.addWidget(btn)
            self.sound_buttons[name] = btn
        root.addLayout(sound_layout)

        # Таймер
        self.max_time = self.max_minutes * 60
        self.remaining_time = 90 * 60
        self.timer_active = False
        self.paused = False
        self.qtimer = QtCore.QTimer()
        self.qtimer.timeout.connect(self.update_countdown)

        # аудио
        self.current_effect = None     # pygame.mixer.Sound для клика
        self.current_sound = None      # имя текущего звука

        # клики и overlay
        self.click_times = []
        self.breathing_overlay = BreathingOverlay(self, on_click=self.on_breathing_click)
        self.breathing_overlay.hide()

        # финальная инициализация UI
        self.update_ui()
        # установим дефолтный звук "Камин" (если есть)
        try:
            self.on_scene_change("fire")
        except Exception:
            # на случай, если что-то не так с файлами, не ломаем запуск
            names = list(MEDIA.keys())
            if names:
                self.on_scene_change(names[0])

        # загрузка эффекта дыхания (если файл существует)
        if os.path.exists(BREATH_CLICK):
            try:
                self.breath_effect = pygame.mixer.Sound(BREATH_CLICK)
            except Exception:
                self.breath_effect = None
        else:
            self.breath_effect = None

        # установим дефолтную сцену (если есть)
        try:
            first_scene = next(iter(SCENES.keys()))
            self.on_scene_change(first_scene)
        except Exception:
            pass

    # ---------------- UI / таймер ----------------

    def update_ui(self) -> None:
        mins = self.remaining_time // 60
        secs = self.remaining_time % 60
        self.label_time.setText(f"Осталось: {mins} мин. {secs:02d} сек.")
        self.slider.blockSignals(True)
        self.slider.setValue(seconds_to_slider(self.remaining_time, self.max_time))
        self.slider.blockSignals(False)

    def on_slider_released(self) -> None:
        self.remaining_time = slider_to_seconds(self.slider.value(), self.max_time)
        self.update_ui()

    def on_action_button(self) -> None:
        if not self.timer_active:
            self.timer_active = True
            self.paused = False
            self.btn_action.setText("Пауза ⏸️")
            self.qtimer.start(1000)
        elif not self.paused:
            self.paused = True
            self.qtimer.stop()
            self.btn_action.setText("Продолжить ▶️")
        else:
            self.paused = False
            self.qtimer.start(1000)
            self.btn_action.setText("Пауза ⏸️")

    def update_countdown(self) -> None:
        if self.timer_active and not self.paused:
            self.remaining_time -= 1
            if self.remaining_time <= 0:
                self.qtimer.stop()
                self.timer_active = False
                self.btn_action.setText("Запустить таймер 🚀")
                # действие по завершению
                if self.btn_shutdown.isChecked():
                    os.system("shutdown /s /t 1")
                elif self.btn_mute.isChecked():
                    VK_VOLUME_MUTE = 0xAD
                    ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 2, 0)
            self.update_ui()

    # ---------------- громкость и звук ----------------

    def change_volume(self, value: int) -> None:
        """Изменение громкости музыки и эффектов (слот получает int)."""
        vol = (value or 0) / 100.0
        try:
            pygame.mixer.music.set_volume(vol)
        except Exception:
            pass
        # текущий эффект (клик)
        if self.current_effect is not None:
            try:
                self.current_effect.set_volume(vol)
            except Exception:
                pass

        self.settings.setValue("vol_is_zero", value == 0)
        self.label_vol.setText(f"Громкость: {value}%")

    def on_scene_change(self, name: str) -> None:
        """Переключение сцены (фон, гиф, звук, эффект клика)."""
        # подсветка плиток
        for n, btn in self.sound_buttons.items():
            btn.setChecked(n == name)

        self.current_sound = name
        files = SCENES.get(name, {})

        # фон (pygame.music)
        wav = files.get('ogg')
        if wav and os.path.exists(wav):
            try:
                pygame.mixer.music.load(wav)
                pygame.mixer.music.set_volume(self.slider_vol.value() / 100.0)
                pygame.mixer.music.play(-1)
            except Exception:
                pass

        # гифка
        gif = files.get('gif')
        if gif and os.path.exists(gif):
            try:
                movie = QtGui.QMovie(gif)
                movie.setScaledSize(QtCore.QSize(240, 240))
                self.gif_label.setMovie(movie)
                movie.start()
            except Exception:
                self.gif_label.clear()
        else:
            self.gif_label.clear()

        # кликовый эффект (tap_ogg)
        sfx = files.get('tap_ogg')
        if sfx and os.path.exists(sfx):
            try:
                snd = pygame.mixer.Sound(sfx)
                snd.set_volume(self.slider_vol.value() / 100.0)
                self.current_effect = snd
            except Exception:
                self.current_effect = None
        else:
            self.current_effect = None

    def on_gif_clicked(self):
        """Обработчик клика по гифке."""
        print("Гифка нажата!")
        # воспроизведение клика-эффекта через свободный канал, с громкостью из ползунка
        if self.current_effect:
            try:
                vol = self.slider_vol.value() / 100.0
                ch = pygame.mixer.find_channel(True)
                if ch:
                    ch.set_volume(vol)
                    ch.play(self.current_effect)
            except Exception:
                pass

        # добавляем клик в историю
        now = time.time()
        self.click_times = [t for t in self.click_times if now - t < 1.5]
        self.click_times.append(now)

        # пасхалка: 5 кликов включают режим дыхания
        if len(self.click_times) >= 5:
            self.click_times.clear()
            self.activate_breathing_mode()

    def on_breathing_click(self) -> None:
        """Клик внутри оверлея дыхания: считаем клики для выхода (8 кликов)."""
        # Воспроизведение клика-эффекта даже в режиме дыхания
        if self.current_effect:
            try:
                vol = self.slider_vol.value() / 100.0
                ch = pygame.mixer.find_channel(True)
                if ch:
                    ch.set_volume(vol)
                    ch.play(self.breath_effect)
            except Exception:
                pass

        now = time.time()
        self.click_times = [t for t in self.click_times if now - t < 1.5]
        self.click_times.append(now)
        # при N кликах — выйти (плавно если оверлей поддерживает outro)
        if len(self.click_times) >= 8:
            self.click_times.clear()
            try:
                self.breathing_overlay.play_outro(self.breathing_overlay.hide)
            except Exception:
                self.breathing_overlay.hide()

    def activate_breathing_mode(self) -> None:
        """Показываем overlay шире гифки с обеих сторон, чтобы шар не обрезался при bounce."""
        try:
            gif_rect = self.gif_label.geometry()
            extra_space = 80  # ширина для кнопки и левого края
            # overlay шире гифки, сдвигаем влево
            self.breathing_overlay.setGeometry(
                self.gif_container.x() + gif_rect.x() - extra_space // 2,
                self.gif_container.y() + gif_rect.y(),
                gif_rect.width() + extra_space,
                gif_rect.height()
            )
            # центр шара = центр гифки, сдвигаем вправо на extra_space // 2
            local_gif_rect = QtCore.QRect(extra_space // 2, 0, gif_rect.width(), gif_rect.height())
            self.breathing_overlay.set_gif_geometry(local_gif_rect)
            try:
                self.breathing_overlay.play_intro()
            except Exception:
                self.breathing_overlay.show()
            self.breathing_overlay.raise_()
        except Exception:
            try:
                self.breathing_overlay.show()
                self.breathing_overlay.raise_()
            except Exception:
                pass

    def resizeEvent(self, e: QtGui.QResizeEvent):
        try:
            # обновим breathing_overlay
            if self.breathing_overlay.isVisible():
                gif_rect = self.gif_container.geometry()
                extra_space = 80  # должно совпадать с activate_breathing_mode!
                self.breathing_overlay.setGeometry(
                    gif_rect.x() - extra_space // 2,
                    gif_rect.y(),
                    gif_rect.width() + extra_space,
                    gif_rect.height()
                )
                # центр шара = центр гифки, сдвигаем вправо на extra_space // 2
                local_gif_rect = QtCore.QRect(extra_space // 2, 0, gif_rect.width(), gif_rect.height())
                self.breathing_overlay.set_gif_geometry(local_gif_rect)
                self.breathing_overlay.raise_()
        except Exception:
            pass

        try:
            # обновим gif_animator
            if self.gif_animator.isVisible():
                self.gif_animator.setGeometry(0, 0, self.gif_container.width(), self.gif_container.height())
                self.gif_animator.raise_()
        except Exception:
            pass

        super().resizeEvent(e)


    def mute_sound(self) -> None:
        VK_VOLUME_MUTE = 0xAD
        ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 2, 0)

    def shutdown_pc(self) -> None:
        os.system("shutdown /s /f /t 0")