/**
 * Функции для работы со звуком
 */

// Инициализация аудио системы
function initAudio() {
    try {
        // Создаем аудио контекст
        appState.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        
        // Загружаем аудио файлы для всех сцен
        Object.keys(SCENES).forEach(sceneName => {
            const scene = SCENES[sceneName];
            loadAudioFile(`media/${scene.sound}`, `${sceneName}_bg`);
            if (scene.tapSound) {
                loadAudioFile(`media/${scene.tapSound}`, `${sceneName}_tap`);
            }
        });
        
        // Загружаем звук для режима дыхания
        loadAudioFile('media/breath_tap.ogg', 'breath_tap');
        
    } catch (error) {
        console.error('Ошибка инициализации аудио:', error);
    }
}

// Загрузка аудио файла
function loadAudioFile(url, id) {
    fetch(url)
        .then(response => response.arrayBuffer())
        .then(arrayBuffer => appState.audioContext.decodeAudioData(arrayBuffer))
        .then(audioBuffer => {
            appState.audioBuffers[id] = audioBuffer;
            console.log(`Аудио файл загружен: ${id}`);
            
            // Если это фоновый звук текущей сцены, начинаем его воспроизведение
            if (id === `${appState.currentScene}_bg`) {
                playBackgroundSound(appState.currentScene);
            }
        })
        .catch(error => console.error(`Ошибка загрузки аудио ${id}:`, error));
}

// Воспроизведение фонового звука
function playBackgroundSound(sceneName) {
    const bufferId = `${sceneName}_bg`;
    
    // Останавливаем предыдущий звук, если есть
    stopAllAudio();
    
    // Если буфер загружен, воспроизводим его
    if (appState.audioBuffers[bufferId]) {
        const source = appState.audioContext.createBufferSource();
        source.buffer = appState.audioBuffers[bufferId];
        source.loop = true;
        
        // Создаем узел громкости
        const gainNode = appState.audioContext.createGain();
        gainNode.gain.value = appState.volume / 100;
        
        // Подключаем
        source.connect(gainNode);
        gainNode.connect(appState.audioContext.destination);
        
        // Запоминаем источник и регулятор громкости
        appState.audioSources.background = {
            source: source,
            gain: gainNode
        };
        
        // Воспроизводим
        source.start();
    }
}

// Воспроизведение звука нажатия
function playTapSound() {
    const bufferId = `${appState.currentScene}_tap`;
    
    if (appState.audioBuffers[bufferId]) {
        const source = appState.audioContext.createBufferSource();
        source.buffer = appState.audioBuffers[bufferId];
        
        // Создаем узел громкости
        const gainNode = appState.audioContext.createGain();
        gainNode.gain.value = appState.volume / 100;
        
        // Подключаем
        source.connect(gainNode);
        gainNode.connect(appState.audioContext.destination);
        
        // Воспроизводим
        source.start();
    }
}

// Воспроизведение звука нажатия в режиме дыхания
function playBreathTapSound() {
    const bufferId = 'breath_tap';
    
    if (appState.audioBuffers[bufferId]) {
        const source = appState.audioContext.createBufferSource();
        source.buffer = appState.audioBuffers[bufferId];
        
        // Создаем узел громкости
        const gainNode = appState.audioContext.createGain();
        gainNode.gain.value = appState.volume / 100;
        
        // Подключаем
        source.connect(gainNode);
        gainNode.connect(appState.audioContext.destination);
        
        // Воспроизводим
        source.start();
    }
}

// Установка громкости
function setVolume(volume) {
    // Устанавливаем громкость для всех активных источников
    Object.values(appState.audioSources).forEach(audioSource => {
        if (audioSource.gain) {
            audioSource.gain.gain.value = volume;
        }
    });
}

// Остановка всех звуков
function stopAllAudio() {
    // Останавливаем все активные источники
    Object.values(appState.audioSources).forEach(audioSource => {
        if (audioSource.source) {
            try {
                audioSource.source.stop();
            } catch (error) {
                // Источник уже остановлен
            }
        }
    });
    
    // Очищаем список активных источников
    appState.audioSources = {};
}

// Обновление отображения громкости
function updateVolumeLabel() {
    elements.volumeLabel.textContent = `Громкость: ${appState.volume}%`;
}
