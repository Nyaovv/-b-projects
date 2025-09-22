/**
 * Функции для управления таймером
 */

let timerInterval = null;

// Инициализация таймера
function initTimer() {
    // Установка начальных значений таймера
    appState.timerMinutes = parseInt(elements.timerSlider.value);
    appState.timerSeconds = 0;
    updateTimerLabel();
}

// Обновление отображаемого времени таймера
function updateTimerLabel() {
    elements.timerLabel.textContent = `Осталось: ${appState.timerMinutes} мин. ${appState.timerSeconds.toString().padStart(2, '0')} сек.`;
}

// Запуск/пауза таймера
function toggleTimer() {
    if (!appState.timerActive) {
        // Запуск таймера
        startTimer();
    } else if (!appState.paused) {
        // Пауза
        pauseTimer();
    } else {
        // Возобновление
        resumeTimer();
    }
}

// Запуск таймера
function startTimer() {
    appState.timerActive = true;
    appState.paused = false;
    elements.startButton.textContent = 'Пауза ⏸️';
    
    // Запуск интервала
    timerInterval = setInterval(updateTimer, 1000);
    
    // Отключаем возможность изменения таймера
    elements.timerSlider.disabled = true;
}

// Пауза таймера
function pauseTimer() {
    appState.paused = true;
    clearInterval(timerInterval);
    elements.startButton.textContent = 'Продолжить ▶️';
}

// Возобновление таймера
function resumeTimer() {
    appState.paused = false;
    timerInterval = setInterval(updateTimer, 1000);
    elements.startButton.textContent = 'Пауза ⏸️';
}

// Остановка таймера
function stopTimer() {
    appState.timerActive = false;
    appState.paused = false;
    clearInterval(timerInterval);
    elements.startButton.textContent = 'Запустить таймер 🚀';
    
    // Возвращаем возможность изменения таймера
    elements.timerSlider.disabled = false;
    
    // Выполняем действие в зависимости от выбранного режима
    if (appState.timerMinutes === 0 && appState.timerSeconds === 0) {
        if (appState.currentMode === 'exit') {
            // Закрываем мини-приложение
            tg.close();
        } else {
            // Отправляем уведомление о выключении звука
            tg.showAlert('Время вышло! Отключите звук на устройстве.');
        }
    }
}

// Обновление таймера каждую секунду
function updateTimer() {
    if (appState.timerSeconds > 0) {
        appState.timerSeconds--;
    } else if (appState.timerMinutes > 0) {
        appState.timerMinutes--;
        appState.timerSeconds = 59;
    } else {
        // Время истекло
        stopTimer();
    }
    
    // Обновляем отображение времени
    updateTimerLabel();
    
    // Обновляем слайдер
    elements.timerSlider.value = appState.timerMinutes;
}
