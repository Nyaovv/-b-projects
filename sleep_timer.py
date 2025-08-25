import sys
import os
import ctypes
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QStyleOptionSlider, QStyle
import pygame
import math
import random  # Добавлено для случайных значений в частицах

# ---- Аудио ----
pygame.mixer.init()
pygame.mixer.set_num_channels(32)  # чтобы клики могли накладываться

MEDIA = {
    "Белый шум": ("white_noise.ogg", "white_noise.gif", "white_noise.png", "click.ogg"),
    "Камин": ("fire.ogg", "fire.gif", "fire.png", "crack.ogg"),
    "Дождь": ("rain.ogg", "rain.gif", "rain.png", "drop.ogg"),
}

BREATH_CLICK = "breath.ogg"  # отдельный клик для режима дыхания


# ---- Кастомный виджет меток под слайдером ----
class TickLabels(QtWidgets.QWidget):
    def __init__(self, slider: QtWidgets.QSlider, marks_minutes, max_minutes: int):
        super().__init__()
        self.slider = slider
        self.marks = marks_minutes
        self.max_minutes = max_minutes
        self.setFixedHeight(24)

    def paintEvent(self, e):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        pen = QtGui.QPen(QtGui.QColor("#CCCCCC"))  # светлый текст
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


# ---- Кликабельная метка под гифку ----
class ClickableLabel(QtWidgets.QLabel):
    clicked = QtCore.pyqtSignal()
    def mousePressEvent(self, event: QtGui.QMouseEvent):
        self.clicked.emit()
        super().mousePressEvent(event)


# ---- Промежуточный объект для плавного масштабирования QMovie ----
class MovieScaler(QtCore.QObject):
    def __init__(self, label: QtWidgets.QLabel, base_size=QtCore.QSize(240, 240)):
        super().__init__()
        self._scale = 1.0
        self.label = label
        self.base_size = base_size

    @QtCore.pyqtProperty(float)
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, value: float):
        self._scale = float(value)
        movie = self.label.movie()
        if movie:
            w = max(1, int(self.base_size.width() * self._scale))
            h = max(1, int(self.base_size.height() * self._scale))
            movie.setScaledSize(QtCore.QSize(w, h))


# ---- Полупрозрачный оверлей дыхания ----
class BreathingOverlay(QtWidgets.QWidget):
    """Оверлей поверх gif_label с точной по времени анимацией дыхания 4–4–4–4."""
    def __init__(self, parent=None, on_click=None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("background: transparent;")

        # Колбэк для прокидывания клика
        self._on_click = on_click

        # Параметры дыхания (секунды)
        self.t_in = 4.0
        self.t_hold1 = 4.0
        self.t_out = 4.0
        self.t_hold2 = 4.0
        self.cycle = self.t_in + self.t_hold1 + self.t_out + self.t_hold2

        # Таймер перерисовки; фазы считаем по монотонным часам
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(33)  # ~30 FPS
        self._timer.timeout.connect(self.update)
        self._elapsed = QtCore.QElapsedTimer()

        # Кнопка выхода
        self.btn_exit = QtWidgets.QPushButton("ВЕРНУТЬСЯ", self)
        self.btn_exit.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_exit.setStyleSheet(
            """
            QPushButton { font-size: 28pt; font-weight: 900; color: #ffffff; background:#D32F2F; border:none; padding: 4px 16px; border-radius: 10px; }
            QPushButton:hover { background:#B71C1C; }
            """
        )  # Уменьшен шрифт, чтобы текст влезал
        self.btn_exit.clicked.connect(self.hide)

        # Частицы для внутренней анимации
        self.particles = []
        for _ in range(10):  # 10 частиц
            self.particles.append({
                'pos': QtCore.QPointF(0, 0),
                'vel': QtCore.QPointF(0, 0),
                'radius': 5 + random.random() * 10,
                'phase': random.random() * 2 * math.pi
            })

    def showEvent(self, e):
        self._elapsed.start()
        self._timer.start()
        self.update()
        return super().showEvent(e)

    def hideEvent(self, e):
        self._timer.stop()
        return super().hideEvent(e)

    def resizeEvent(self, e):
        self.btn_exit.adjustSize()
        margin = 12
        # Позиционирование кнопки справа от GIF
        gif_width = self.parent().gif_label.width() if self.parent() else self.width() // 2
        self.btn_exit.move(gif_width + margin, margin)
        return super().resizeEvent(e)

    def mousePressEvent(self, e: QtGui.QMouseEvent):
        if callable(self._on_click):
            self._on_click()
        return super().mousePressEvent(e)

    def _radius_for_time(self, t_norm: float, base: float, amp: float) -> float:
        t = t_norm
        if t < self.t_in:  # вдох 0→1
            k = t / self.t_in
            return base + amp * k
        t -= self.t_in
        if t < self.t_hold1:  # пауза на пике
            return base + amp
        t -= self.t_hold1
        if t < self.t_out:  # выдох 1→0
            k = 1.0 - (t / self.t_out)
            return base + amp * k
        return base  # нижняя пауза

    def paintEvent(self, e):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        rect = self.rect()
        center = rect.center()
        min_side = min(rect.width(), rect.height())

        base = 0.20 * min_side
        amp = 0.30 * min_side

        t = (self._elapsed.elapsed() / 1000.0) % self.cycle
        radius = self._radius_for_time(t, base, amp)

        # Затухание: alpha уменьшается на выдохе
        alpha_factor = 1.0
        phase = t % self.cycle
        if phase >= self.t_in + self.t_hold1 and phase < self.t_in + self.t_hold1 + self.t_out:
            elapsed_out = phase - (self.t_in + self.t_hold1)
            alpha_factor = 1.0 - (elapsed_out / self.t_out) * 0.5  # Затухает до 50%

        grad = QtGui.QRadialGradient(center, radius)
        color = QtGui.QColor(144, 202, 249, int(140 * alpha_factor))
        center_color = QtGui.QColor(144, 202, 249, int(70 * alpha_factor))
        grad.setColorAt(0.0, center_color)
        grad.setColorAt(1.0, color)

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QBrush(grad))
        painter.drawEllipse(center, int(radius), int(radius))

        # Внутренние частицы с "физикой" (синусоидальное плавание, реакция на радиус)
        scale_factor = radius / (base + amp / 2)  # Масштаб относительно среднего радиуса
        for p in self.particles:
            p['phase'] += 0.05  # Скорость движения
            offset_x = math.sin(p['phase']) * (radius * 0.4)
            offset_y = math.cos(p['phase']) * (radius * 0.4)
            # "Физика": частицы сжимаются/расширяются с кругом
            p['pos'] = QtCore.QPointF(offset_x * scale_factor, offset_y * scale_factor)

            p_grad = QtGui.QRadialGradient(center + p['pos'], p['radius'])
            p_color = QtGui.QColor(173, 216, 230, int(100 * alpha_factor))
            p_center_color = QtGui.QColor(173, 216, 230, int(50 * alpha_factor))
            p_grad.setColorAt(0.0, p_center_color)
            p_grad.setColorAt(1.0, p_color)
            painter.setBrush(QtGui.QBrush(p_grad))
            painter.drawEllipse(center + p['pos'], int(p['radius']), int(p['radius']))


class SelectableButton(QtWidgets.QPushButton):
    def __init__(self, text, icon=None):
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


# ---- Основное окно ----
class SleepTimer(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Таймер сна 💤")
        self.setGeometry(200, 200, 700, 600)

        # ночной фон
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

        # ----- Время -----
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

        # ----- Большие кнопки режима -----
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

        # ----- Громкость -----
        self.label_vol = QtWidgets.QLabel()
        root.addWidget(self.label_vol)

        self.slider_vol = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_vol.setMinimum(0)
        self.slider_vol.setMaximum(100)
        vol_is_zero = self.settings.value("vol_is_zero", False, type=bool)
        self.slider_vol.setValue(0 if vol_is_zero else 20)
        self.slider_vol.valueChanged.connect(self.change_volume)
        root.addWidget(self.slider_vol)

        # ----- Кнопка запуска ----
        self.btn_action = QtWidgets.QPushButton("Запустить таймер 🚀")
        self.btn_action.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_action.clicked.connect(self.on_action_button)
        self.btn_action.setStyleSheet(
            "padding: 10px 16px; border-radius: 10px; border: 1px solid #666; background: #2E2E2E; font-weight: 600; color: #DDDDDD;"
        )
        root.addWidget(self.btn_action)

        # ----- Центральная гифка -----
        self.gif_label = ClickableLabel(alignment=QtCore.Qt.AlignCenter)
        root.addWidget(self.gif_label, alignment=QtCore.Qt.AlignCenter)

        # Баунс через масштабирование QMovie
        self.scaler = MovieScaler(self.gif_label, QtCore.QSize(240, 240))
        self.bounce_anim = QtCore.QPropertyAnimation(self.scaler, b"scale")
        self.bounce_anim.setDuration(260)
        self.bounce_anim.setEasingCurve(QtCore.QEasingCurve.InOutCubic)
        self.gif_label.clicked.connect(self.on_gif_clicked)

        # ----- Плитки выбора звука -----
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

        # ----- Таймер -----
        self.max_time = self.max_minutes * 60
        self.remaining_time = 90 * 60
        self.timer_active = False
        self.paused = False
        self.qtimer = QtCore.QTimer()
        self.qtimer.timeout.connect(self.update_countdown)

        # ---- Звуковые эффекты ----
        self.current_effect = None

        # ---- Логика "5 кликов за ≤1.5 c" ----
        self.click_times = []
        self.breathing_overlay = BreathingOverlay(self, on_click=self.on_breathing_click)
        self.breathing_overlay.hide()

        self.update_ui()
        self.on_sound_change("Камин")  # дефолт

    # ---- Время ----
    def seconds_to_slider(self, seconds):
        return int((seconds / self.max_time) * 1000)

    def slider_to_seconds(self, value):
        return max(60, int((value / 1000) * self.max_time))

    def update_ui(self):
        mins = self.remaining_time // 60
        secs = self.remaining_time % 60
        self.label_time.setText(f"Осталось: {mins} мин. {secs:02d} сек.")
        self.slider.blockSignals(True)
        self.slider.setValue(self.seconds_to_slider(self.remaining_time))
        self.slider.blockSignals(False)

    # ---- Громкость ----
    def change_volume(self):
        vol = self.slider_vol.value()
        pygame.mixer.music.set_volume(vol / 100)
        self.label_vol.setText(f"Громкость: {vol}%")
        self.settings.setValue("vol_is_zero", vol == 0)

    # ---- Звук и гифка ----
    def on_sound_change(self, name):
        for n, btn in self.sound_buttons.items():
            btn.setChecked(n == name)

        wav, gif, preview, sfx = MEDIA[name]
        # Основной фон
        if os.path.exists(wav):
            try:
                pygame.mixer.music.load(wav)
                pygame.mixer.music.set_volume(self.slider_vol.value() / 100)
                pygame.mixer.music.play(-1)
            except Exception:
                pass
        # Гифка
        if gif and os.path.exists(gif):
            movie = QtGui.QMovie(gif)
            movie.setScaledSize(QtCore.QSize(240, 240))
            self.gif_label.setMovie(movie)
            movie.start()
        else:
            self.gif_label.clear()
        # Клик-эффект
        self.current_effect = pygame.mixer.Sound(sfx) if os.path.exists(sfx) else None

    # ---- Клик по гифке ----
    def on_gif_clicked(self):
        now = QtCore.QTime.currentTime().msecsSinceStartOfDay()
        # оставляем только клики в пределах 1.5 сек
        self.click_times = [t for t in self.click_times if now - t < 1500]
        self.click_times.append(now)
        if len(self.click_times) >= 5:
            self.activate_breathing_mode()
            self.click_times.clear()
            return

        # Обычный режим: уменьшающийся bounce + наложение эффекта на свободном канале
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
            # Если открыт дыхательный оверлей — клики ловятся им, но на всякий случай:
            self.on_breathing_click()

    def on_breathing_click(self):
        # Инвертированный bounce (увеличиваем гифку) и отдельный звук дыхательного режима
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

    def activate_breathing_mode(self):
        # Расширяем оверлей вправо для места под кнопку
        gif_rect = self.gif_label.geometry()
        extra_space = 200  # Дополнительное пространство справа
        self.breathing_overlay.setGeometry(gif_rect.x(), gif_rect.y(), gif_rect.width() + extra_space, gif_rect.height())
        self.breathing_overlay.show()
        self.breathing_overlay.raise_()

    def resizeEvent(self, e: QtGui.QResizeEvent):
        if self.breathing_overlay.isVisible():
            gif_rect = self.gif_label.geometry()
            extra_space = 200
            self.breathing_overlay.setGeometry(gif_rect.x(), gif_rect.y(), gif_rect.width() + extra_space, gif_rect.height())
            self.breathing_overlay.raise_()
        return super().resizeEvent(e)

    # ---- Кнопка действия ----
    def on_action_button(self):
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

    def start_timer(self):
        self.timer_active = True
        self.paused = False
        self.qtimer.start(1000)

    def update_countdown(self):
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

    def on_slider_released(self):
        self.remaining_time = self.slider_to_seconds(self.slider.value())
        self.update_ui()

    # ---- Действия завершения ----
    def mute_sound(self):
        VK_VOLUME_MUTE = 0xAD
        ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 2, 0)

    def shutdown_pc(self):
        os.system("shutdown /s /f /t 0")


# ---- Запуск ----
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = SleepTimer()
    window.show()
    sys.exit(app.exec_())
