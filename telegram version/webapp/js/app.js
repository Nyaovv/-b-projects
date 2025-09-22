/**
 * RestApp - Telegram Mini App версия
 * Основной скрипт приложения
 */

// Инициализация Telegram Mini App
let tg = window.Telegram.WebApp;

// Данные текущего пользователя
let userData = {
    id: tg.initDataUnsafe?.user?.id || 0,
    settings: {
        volume: 50,
        timer: 90,
        scene: 'fire',
        mode: 'mute'
    }
};

// Состояние приложения
const appState = {
    currentScene: 'fire',
    timerActive: false,
    paused: false,
    breathingMode: false,
    clickTimes: [],
    volume: 50,
    timerMinutes: 90,
    timerSeconds: 0,
    currentMode: 'mute',
    audioContext: null,
    audioBuffers: {},
    audioSources: {},
    breathingPhase: 'hold',
};

// DOM элементы
const elements = {
    timerLabel: document.getElementById('timer-label'),
    timerSlider: document.getElementById('timer-slider'),
    volumeSlider: document.getElementById('volume-slider'),
    volumeLabel: document.getElementById('volume-label'),
    startButton: document.getElementById('start-button'),
    muteMode: document.getElementById('mute-mode'),
    exitMode: document.getElementById('exit-mode'),
    sceneImage: document.getElementById('scene-image'),
    scenes: document.querySelectorAll('.scene'),
    breathingOverlay: document.getElementById('breathing-overlay'),
    breathingExit: document.getElementById('breathing-exit'),
    breathingCircle: document.getElementById('breathing-circle'),
    breathText: document.getElementById('breath-text')
};

// Константы для сцен
const SCENES = {
    fire: {
        name: 'Камин',
        sound: 'fire.ogg',
        animation: 'fire.gif',
        thumbnail: 'fire.png',
        tapSound: 'crack.ogg'
    },
    rain: {
        name: 'Дождь',
        sound: 'rain.ogg',
        animation: 'rain.gif',
        thumbnail: 'rain.png',
        tapSound: 'drop.ogg'
    },
    white_noise: {
        name: 'Белый шум',
        sound: 'white_noise.ogg',
        animation: 'white_noise.gif',
        thumbnail: 'white_noise.png',
        tapSound: 'click.ogg'
    }
};

// Инициализация приложения
document.addEventListener('DOMContentLoaded', () => {
    // Применяем тему Telegram
    applyTelegramTheme();
    
    // Загружаем настройки пользователя
    loadUserSettings();
    
    // Инициализация интерфейса
    initUI();
    
    // Инициализация WebAudio API
    initAudio();
    
    // Инициализация таймера
    initTimer();
    
    // Инициализация режима дыхания
    initBreathingMode();
    
    // Устанавливаем начальную сцену
    changeScene(appState.currentScene);
    
    // Сообщаем Telegram, что приложение готово
    tg.ready();
    tg.expand();
});

// Применяем тему Telegram
function applyTelegramTheme() {
    document.body.classList.add('telegram-app');
    
    // Установка цветов из темы Telegram
    if (tg.colorScheme === 'dark') {
        document.documentElement.style.setProperty('--bg-color', '#1E1E1E');
        document.documentElement.style.setProperty('--text-color', '#FFFFFF');
    } else {
        document.documentElement.style.setProperty('--bg-color', '#F5F5F5');
        document.documentElement.style.setProperty('--text-color', '#333333');
    }
    
    // Установка акцентного цвета из темы Telegram, если есть
    if (tg.themeParams && tg.themeParams.accent_color) {
        document.documentElement.style.setProperty('--accent-color', tg.themeParams.accent_color);
    }
}

// Загрузка настроек пользователя
function loadUserSettings() {
    // Если у нас есть ID пользователя, пробуем загрузить его настройки
    if (userData.id) {
        fetch(`/api/settings/${userData.id}`)
            .then(response => response.json())
            .then(data => {
                if (data.success && data.settings) {
                    userData.settings = data.settings;
                    appState.volume = userData.settings.volume;
                    appState.timerMinutes = userData.settings.timer;
                    appState.currentScene = userData.settings.scene;
                    appState.currentMode = userData.settings.mode;
                    
                    // Применяем загруженные настройки
                    applyUserSettings();
                }
            })
            .catch(error => console.error('Ошибка загрузки настроек:', error));
    }
}

// Применение загруженных настроек
function applyUserSettings() {
    elements.timerSlider.value = appState.timerMinutes;
    elements.volumeSlider.value = appState.volume;
    updateTimerLabel();
    updateVolumeLabel();
    
    // Установка режима
    if (appState.currentMode === 'mute') {
        elements.muteMode.classList.add('active');
        elements.exitMode.classList.remove('active');
    } else {
        elements.exitMode.classList.add('active');
        elements.muteMode.classList.remove('active');
    }
    
    // Установка сцены
    changeScene(appState.currentScene);
}

// Сохранение настроек пользователя
function saveUserSettings() {
    if (userData.id) {
        const settings = {
            volume: appState.volume,
            timer: appState.timerMinutes,
            scene: appState.currentScene,
            mode: appState.currentMode
        };
        
        fetch(`/api/settings/${userData.id}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log('Настройки сохранены');
                
                // Отправляем данные обратно в Telegram
                tg.sendData(JSON.stringify(settings));
            }
        })
        .catch(error => console.error('Ошибка сохранения настроек:', error));
    }
}

// Инициализация пользовательского интерфейса
function initUI() {
    // Обработчики для слайдера таймера
    elements.timerSlider.addEventListener('input', () => {
        appState.timerMinutes = parseInt(elements.timerSlider.value);
        appState.timerSeconds = 0;
        updateTimerLabel();
        saveUserSettings();
    });
    
    // Обработчики для слайдера громкости
    elements.volumeSlider.addEventListener('input', () => {
        appState.volume = parseInt(elements.volumeSlider.value);
        updateVolumeLabel();
        setVolume(appState.volume / 100);
        saveUserSettings();
    });
    
    // Обработчик для кнопки старта/паузы таймера
    elements.startButton.addEventListener('click', toggleTimer);
    
    // Обработчики для кнопок режимов
    elements.muteMode.addEventListener('click', () => {
        elements.muteMode.classList.add('active');
        elements.exitMode.classList.remove('active');
        appState.currentMode = 'mute';
        saveUserSettings();
    });
    
    elements.exitMode.addEventListener('click', () => {
        elements.exitMode.classList.add('active');
        elements.muteMode.classList.remove('active');
        appState.currentMode = 'exit';
        saveUserSettings();
    });
    
    // Обработчики для сцен
    elements.scenes.forEach(scene => {
        scene.addEventListener('click', () => {
            const sceneName = scene.dataset.scene;
            changeScene(sceneName);
            saveUserSettings();
        });
    });
    
    // Обработчик для нажатия на анимацию (GIF)
    elements.sceneImage.addEventListener('click', handleGifClick);
    
    // Обработчик для кнопки выхода из режима дыхания
    elements.breathingExit.addEventListener('click', exitBreathingMode);
    
    // Обработчик нажатий в режиме дыхания
    elements.breathingOverlay.addEventListener('click', handleBreathingClick);
}

// Обработка нажатия на GIF
function handleGifClick() {
    // Воспроизведение звука нажатия
    playTapSound();
    
    // Анимация нажатия (баунс)
    elements.sceneImage.classList.add('bounce');
    setTimeout(() => {
        elements.sceneImage.classList.remove('bounce');
    }, 300);
    
    // Учет времени нажатия для активации режима дыхания
    const now = Date.now();
    appState.clickTimes = appState.clickTimes.filter(t => now - t < 1500);
    appState.clickTimes.push(now);
    
    // Активация режима дыхания после 5 быстрых нажатий
    if (appState.clickTimes.length >= 5) {
        appState.clickTimes = [];
        activateBreathingMode();
    }
}

// Изменение текущей сцены
function changeScene(sceneName) {
    // Обновляем текущую сцену
    appState.currentScene = sceneName;
    
    // Обновляем активную сцену в интерфейсе
    elements.scenes.forEach(scene => {
        if (scene.dataset.scene === sceneName) {
            scene.classList.add('active');
        } else {
            scene.classList.remove('active');
        }
    });
    
    // Обновляем анимацию
    const sceneData = SCENES[sceneName];
    elements.sceneImage.src = `assets/${sceneData.animation}`;
    
    // Обновляем фоновый звук
    playBackgroundSound(sceneName);
}

// Инициализация и другие функции будут импортированы из отдельных модулей
