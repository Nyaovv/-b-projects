"""Модуль с UI-классами."""

import os
import ctypes
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QStyleOptionSlider, QStyle
import pygame
import math
import random
from .audio import MEDIA, BREATH_CLICK
from .utils import seconds_to_slider, slider_to_seconds

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
        pen = QtGui.QPen(QtGui.QColor("#CCCCCC"))  # Светлый текст
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
            if m == 10:
                x += 6
            if m == 240:
                x -= 12  # Увеличен сдвиг влево для "240"
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

class BreathingOverlay(QtWidgets.QWidget):
    """Оверлей для дыхательной анимации 4-4-4-4."""

    def __init__(self, parent: QtWidgets.QWidget = None, on_click: callable = None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("background: transparent;")

        self._on_click = on_click

        self.t_in = 4.0
        self.t_hold1 = 4.0
        self.t_out = 4.0
        self.t_hold2 = 4.0
        self.cycle = self.t_in + self.t_hold1 + self.t_out + self.t_hold2

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(33)  # ~30 FPS
        self._timer.timeout.connect(self.update)
        self._elapsed = QtCore.QElapsedTimer()

        self.btn_exit = QtWidgets.QPushButton("ВЕРНУТЬСЯ", self)
        self.btn_exit.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_exit.setStyleSheet(
            """
            QPushButton { font-size: 28pt; font-weight: 900; color: #ffffff; background:#D32F2F; border:none; padding: 4px 16px; border-radius: 10px; }
            QPushButton:hover { background:#B71C1C; }
            """
        )
        self.btn_exit.clicked.connect(self.hide)

        self.particles = []
        for _ in range(10):
            self.particles.append({
                'pos': QtCore.QPointF(0, 0),
                'vel': QtCore.QPointF(0, 0),
                'radius': 5 + random.random() * 10,
                'phase': random.random() * 2 * math.pi
            })

    def showEvent(self, e: QtGui.QShowEvent) -> None:
        self._elapsed.start()
        self._timer.start()
        self.update()
        super().showEvent(e)

    def hideEvent(self, e: QtGui.QHideEvent) -> None:
        self._timer.stop()
        super().hideEvent(e)

    def resizeEvent(self, e: QtGui.QResizeEvent) -> None:
        self.btn_exit.adjustSize()
        margin = 12
        gif_width = self.parent().gif_label.width() if self.parent() else self.width() // 2
        self.btn_exit.move(gif_width + margin, margin)
        super().resizeEvent(e)

    def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
        if callable(self._on_click):
            self._on_click()
        super().mousePressEvent(e)

    def _radius_for_time(self, t_norm: float, base: float, amp: float) -> float:
        t = t_norm
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

    def paintEvent(self, e: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        rect = self.rect()
        center = rect.center()
        min_side = min(rect.width(), rect.height())

        base = 0.20 * min_side
        amp = 0.30 * min_side

        t = (self._elapsed.elapsed() / 1000.0) % self.cycle
        radius = self._radius_for_time(t, base, amp)

        alpha_factor = 1.0
        phase = t % self.cycle
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

class SleepTimer(QtWidgets.QWidget):
    """Основное окно приложения."""

    def __init__(self):
        super().__init__()
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

        self.label_vol = QtWidgets.QLabel()
        root.addWidget(self.label_vol)

        self.slider_vol = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_vol.setMinimum(0)
        self.slider_vol.setMaximum(100)
        vol_is_zero = self.settings.value("vol_is_zero", False, type=bool)
        self.slider_vol.setValue(0 if vol_is_zero else 20)
        self.slider_vol.valueChanged.connect(self.change_volume)
        root.addWidget(self.slider_vol)

        self.btn_action = QtWidgets.QPushButton("Запустить таймер 🚀")
        self.btn_action.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_action.clicked.connect(self.on_action_button)
        self.btn_action.setStyleSheet(
            "padding: 10px 16px; border-radius: 10px; border: 1px solid #666; background: #2E2E2E; font-weight: 600; color: #DDDDDD;"
        )
        root.addWidget(self.btn_action)

        self.gif_label = ClickableLabel(alignment=QtCore.Qt.AlignCenter)
        root.addWidget(self.gif_label, alignment=QtCore.Qt.AlignCenter)

        self.scaler = MovieScaler(self.gif_label, QtCore.QSize(240, 240))
        self.bounce_anim = QtCore.QPropertyAnimation(self.scaler, b"scale")
        self.bounce_anim.setDuration(260)
        self.bounce_anim.setEasingCurve(QtCore.QEasingCurve.InOutCubic)
        self.gif_label.clicked.connect(self.on_gif_clicked)

        sound_layout = QtWidgets.QHBoxLayout()
        self.sound_buttons = {}
        for name, (wav, gif, preview, sfx) in MEDIA.items():
            btn = SelectableButton("", preview)
            btn.setIcon(QtGui.QIcon(preview))
            btn.setIconSize(QtCore.QSize(96, 96))
            btn.clicked.connect(lambda _, n=name: self.on_sound_change(n))
            sound_layout.addWidget(btn)
            self.sound_buttons[name] = btn
        root.addLayout(sound_layout)

        self.max_time = self.max_minutes * 60
        self.remaining_time = 90 * 60
        self.timer_active = False
        self.paused = False
        self.qtimer = QtCore.QTimer()
        self.qtimer.timeout.connect(self.update_countdown)

        self.current_effect = None

        self.click_times = []
        self.breathing_overlay = BreathingOverlay(self, on_click=self.on_breathing_click)
        self.breathing_overlay.hide()

        self.update_ui()
        self.on_sound_change("Камин")

    def update_ui(self) -> None:
        mins = self.remaining_time // 60
        secs = self.remaining_time % 60
        self.label_time.setText(f"Осталось: {mins} мин. {secs:02d} сек.")
        self.slider.blockSignals(True)
        self.slider.setValue(seconds_to_slider(self.remaining_time, self.max_time))
        self.slider.blockSignals(False)

    def change_volume(self) -> None:
        vol = self.slider_vol.value()
        pygame.mixer.music.set_volume(vol / 100)
        self.label_vol.setText(f"Громкость: {vol}%")
        self.settings.setValue("vol_is_zero", vol == 0)

    def on_sound_change(self, name: str) -> None:
        for n, btn in self.sound_buttons.items():
            btn.setChecked(n == name)

        wav, gif, preview, sfx = MEDIA[name]
        if os.path.exists(wav):
            try:
                pygame.mixer.music.load(wav)
                pygame.mixer.music.set_volume(self.slider_vol.value() / 100)
                pygame.mixer.music.play(-1)
            except Exception:
                pass
        if gif and os.path.exists(gif):
            movie = QtGui.QMovie(gif)
            movie.setScaledSize(QtCore.QSize(240, 240))
            self.gif_label.setMovie(movie)
            movie.start()
        else:
            self.gif_label.clear()
        self.current_effect = pygame.mixer.Sound(sfx) if os.path.exists(sfx) else None

    def on_gif_clicked(self) -> None:
        now = QtCore.QTime.currentTime().msecsSinceStartOfDay()
        self.click_times = [t for t in self.click_times if now - t < 1500]
        self.click_times.append(now)
        if len(self.click_times) >= 5:
            self.activate_breathing_mode()
            self.click_times.clear()
            return

        if not self.breathing_overlay.isVisible():
            self.bounce_anim.stop()
            self.bounce_anim.setStartValue(1.0)
            self.bounce_anim.setKeyValueAt(0.5, 0.9)
            self.bounce_anim.setEndValue(1.0)
            self.bounce_anim.start()
            if self.current_effect:
                ch = pygame.mixer.find_channel(True)
                if ch:
                    ch.play(self.current_effect)
        else:
            self.on_breathing_click()

    def on_breathing_click(self) -> None:
        self.bounce_anim.stop()
        self.bounce_anim.setStartValue(1.0)
        self.bounce_anim.setKeyValueAt(0.5, 1.15)
        self.bounce_anim.setEndValue(1.0)
        self.bounce_anim.start()
        if os.path.exists(BREATH_CLICK):
            try:
                s = pygame.mixer.Sound(BREATH_CLICK)
                ch = pygame.mixer.find_channel(True)
                if ch:
                    ch.play(s)
            except Exception:
                pass

    def activate_breathing_mode(self) -> None:
        gif_rect = self.gif_label.geometry()
        extra_space = 200
        self.breathing_overlay.setGeometry(gif_rect.x(), gif_rect.y(), gif_rect.width() + extra_space, gif_rect.height())
        self.breathing_overlay.show()
        self.breathing_overlay.raise_()

    def resizeEvent(self, e: QtGui.QResizeEvent) -> None:
        if self.breathing_overlay.isVisible():
            gif_rect = self.gif_label.geometry()
            extra_space = 200
            self.breathing_overlay.setGeometry(gif_rect.x(), gif_rect.y(), gif_rect.width() + extra_space, gif_rect.height())
            self.breathing_overlay.raise_()
        super().resizeEvent(e)

    def on_action_button(self) -> None:
        if not self.timer_active:
            self.start_timer()
            self.btn_action.setText("Пауза ⏸️")
        elif not self.paused:
            self.qtimer.stop()
            self.paused = True
            self.btn_action.setText("Продолжить ▶️")
        else:
            self.qtimer.start(1000)
            self.paused = False
            self.btn_action.setText("Пауза ⏸️")

    def start_timer(self) -> None:
        self.timer_active = True
        self.paused = False
        self.qtimer.start(1000)

    def update_countdown(self) -> None:
        if self.remaining_time > 0:
            self.remaining_time -= 1
            self.update_ui()
        else:
            self.qtimer.stop()
            self.timer_active = False
            self.btn_action.setText("Запустить таймер 🚀")
            if self.btn_mute.isChecked():
                self.mute_sound()
            else:
                self.shutdown_pc()

    def on_slider_released(self) -> None:
        self.remaining_time = slider_to_seconds(self.slider.value(), self.max_time)
        self.update_ui()

    def mute_sound(self) -> None:
        VK_VOLUME_MUTE = 0xAD
        ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 2, 0)

    def shutdown_pc(self) -> None:
        os.system("shutdown /s /f /t 0")
