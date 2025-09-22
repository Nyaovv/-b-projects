/**
 * Функции для режима дыхания
 */

// Настройки режима дыхания
const breathingSettings = {
    inhaleTime: 4.0, // время вдоха (секунды)
    hold1Time: 4.0,  // время задержки после вдоха
    exhaleTime: 4.0, // время выдоха
    hold2Time: 4.0,  // время задержки после выдоха
    
    // Параметры круга
    baseRadius: 50,  // базовый радиус круга (пиксели)
    maxRadius: 150,  // максимальный радиус круга (пиксели)
    
    // Тексты для разных фаз
    texts: {
        inhale: ["вдох", "наберите воздуха", "вдохните", "глубоко вдохните"],
        exhale: ["выдох", "выдохните", "медленный выдох", "пусть уйдёт воздух"],
        hold: ["задержите дыхание", "пауза", "не дышите", "держите"]
    }
};

// Состояние режима дыхания
let breathingState = {
    active: false,
    startTime: 0,
    lastPhase: '',
    currentText: '',
    particles: [],
    textParticles: [],
    clickCount: 0,
    lastClickTime: 0
};

let breathingInterval = null;
let breathTextInterval = null;

// Инициализация режима дыхания
function initBreathingMode() {
    // Создаем частицы для режима дыхания
    for (let i = 0; i < 10; i++) {
        breathingState.particles.push({
            radius: 5 + Math.random() * 10,
            phase: Math.random() * 2 * Math.PI,
            x: 0,
            y: 0
        });
    }
}

// Активация режима дыхания
function activateBreathingMode() {
    breathingState.active = true;
    breathingState.startTime = Date.now();
    breathingState.clickCount = 0;
    breathingState.lastPhase = '';
    
    // Показываем оверлей дыхания
    elements.breathingOverlay.classList.remove('hidden');
    elements.breathingOverlay.classList.add('fade-in');
    
    // Запускаем интервал обновления
    breathingInterval = setInterval(updateBreathingAnimation, 16);
    breathTextInterval = setInterval(updateBreathingPhase, 100);
    
    // Останавливаем все звуки
    stopAllAudio();
    
    // Воспроизводим звук дыхания, если он есть
    playBreathingSound();
}

// Выход из режима дыхания
function exitBreathingMode() {
    breathingState.active = false;
    
    // Скрываем оверлей дыхания
    elements.breathingOverlay.classList.remove('fade-in');
    setTimeout(() => {
        elements.breathingOverlay.classList.add('hidden');
    }, 300);
    
    // Останавливаем интервалы
    clearInterval(breathingInterval);
    clearInterval(breathTextInterval);
    
    // Останавливаем звук дыхания
    stopBreathingSound();
    
    // Восстанавливаем фоновую музыку
    playBackgroundSound(appState.currentScene);
}

// Обработка клика в режиме дыхания
function handleBreathingClick() {
    const now = Date.now();
    
    // Учитываем только клики в течение последних 1.5 секунд
    if (now - breathingState.lastClickTime > 1500) {
        breathingState.clickCount = 0;
    }
    
    breathingState.clickCount++;
    breathingState.lastClickTime = now;
    
    // Добавляем эффект пульсации
    elements.breathingCircle.classList.add('bounce');
    setTimeout(() => {
        elements.breathingCircle.classList.remove('bounce');
    }, 300);
    
    // Воспроизводим звук дыхания
    playBreathTapSound();
    
    // Выход из режима дыхания после 8 быстрых нажатий
    if (breathingState.clickCount >= 8) {
        exitBreathingMode();
    }
}

// Обновление анимации дыхания
function updateBreathingAnimation() {
    if (!breathingState.active) return;
    
    const elapsed = (Date.now() - breathingState.startTime) / 1000;
    const cycleTime = breathingSettings.inhaleTime + breathingSettings.hold1Time + 
                      breathingSettings.exhaleTime + breathingSettings.hold2Time;
    const t = elapsed % cycleTime;
    
    // Определяем текущий радиус круга на основе фазы цикла
    let radius = breathingSettings.baseRadius;
    const radiusRange = breathingSettings.maxRadius - breathingSettings.baseRadius;
    
    if (t < breathingSettings.inhaleTime) {
        // Вдох - увеличиваем радиус
        const progress = t / breathingSettings.inhaleTime;
        radius = breathingSettings.baseRadius + radiusRange * progress;
    } else if (t < breathingSettings.inhaleTime + breathingSettings.hold1Time) {
        // Задержка после вдоха - максимальный радиус
        radius = breathingSettings.maxRadius;
    } else if (t < breathingSettings.inhaleTime + breathingSettings.hold1Time + breathingSettings.exhaleTime) {
        // Выдох - уменьшаем радиус
        const progress = (t - breathingSettings.inhaleTime - breathingSettings.hold1Time) / breathingSettings.exhaleTime;
        radius = breathingSettings.maxRadius - radiusRange * progress;
    } else {
        // Задержка после выдоха - минимальный радиус
        radius = breathingSettings.baseRadius;
    }
    
    // Обновляем размер и положение круга дыхания
    updateBreathingCircle(radius);
    
    // Обновляем положение частиц
    updateBreathingParticles(radius);
}

// Обновление положения и размера круга дыхания
function updateBreathingCircle(radius) {
    const overlay = elements.breathingOverlay;
    const circle = elements.breathingCircle;
    
    // Центрируем круг в оверлее
    const centerX = overlay.clientWidth / 2;
    const centerY = overlay.clientHeight / 2;
    
    circle.style.width = `${radius * 2}px`;
    circle.style.height = `${radius * 2}px`;
    circle.style.left = `${centerX - radius}px`;
    circle.style.top = `${centerY - radius}px`;
}

// Обновление положения частиц вокруг круга дыхания
function updateBreathingParticles(mainRadius) {
    // Удаляем существующие частицы
    const existingParticles = elements.breathingOverlay.querySelectorAll('.particle');
    existingParticles.forEach(p => p.remove());
    
    // Центр круга дыхания
    const overlay = elements.breathingOverlay;
    const centerX = overlay.clientWidth / 2;
    const centerY = overlay.clientHeight / 2;
    
    // Обновляем положение каждой частицы
    breathingState.particles.forEach((particle, index) => {
        // Обновляем фазу
        particle.phase += 0.02;
        
        // Вычисляем новое положение
        const distanceFactor = mainRadius * 0.4; // 40% от радиуса круга
        const offsetX = Math.sin(particle.phase) * distanceFactor;
        const offsetY = Math.cos(particle.phase) * distanceFactor;
        
        particle.x = centerX + offsetX;
        particle.y = centerY + offsetY;
        
        // Создаем элемент частицы
        const particleEl = document.createElement('div');
        particleEl.className = 'particle';
        particleEl.style.width = `${particle.radius * 2}px`;
        particleEl.style.height = `${particle.radius * 2}px`;
        particleEl.style.left = `${particle.x - particle.radius}px`;
        particleEl.style.top = `${particle.y - particle.radius}px`;
        
        // Добавляем частицу в DOM
        elements.breathingOverlay.appendChild(particleEl);
    });
}

// Обновление текущей фазы дыхания и текста
function updateBreathingPhase() {
    if (!breathingState.active) return;
    
    const elapsed = (Date.now() - breathingState.startTime) / 1000;
    const cycleTime = breathingSettings.inhaleTime + breathingSettings.hold1Time + 
                      breathingSettings.exhaleTime + breathingSettings.hold2Time;
    const t = elapsed % cycleTime;
    
    // Определяем текущую фазу
    let phase;
    let phaseDuration;
    
    if (t < breathingSettings.inhaleTime) {
        phase = 'inhale';
        phaseDuration = breathingSettings.inhaleTime;
    } else if (t < breathingSettings.inhaleTime + breathingSettings.hold1Time) {
        phase = 'hold';
        phaseDuration = breathingSettings.hold1Time;
    } else if (t < breathingSettings.inhaleTime + breathingSettings.hold1Time + breathingSettings.exhaleTime) {
        phase = 'exhale';
        phaseDuration = breathingSettings.exhaleTime;
    } else {
        phase = 'hold';
        phaseDuration = breathingSettings.hold2Time;
    }
    
    // Если фаза изменилась, выбираем новый текст
    if (phase !== breathingState.lastPhase) {
        breathingState.lastPhase = phase;
        
        // Выбираем случайный текст для фазы
        const texts = breathingSettings.texts[phase];
        const randomText = texts[Math.floor(Math.random() * texts.length)];
        breathingState.currentText = randomText;
        
        // Обновляем текст на экране
        elements.breathText.textContent = randomText;
        
        // Анимируем появление текста
        elements.breathText.style.opacity = '0';
        setTimeout(() => {
            elements.breathText.style.opacity = '1';
        }, 100);
    }
}

// Воспроизведение звука дыхания
function playBreathingSound() {
    // Здесь можно воспроизвести фоновый звук для режима дыхания, если он есть
}

// Воспроизведение звука нажатия в режиме дыхания
function playBreathTapSound() {
    // Здесь можно воспроизвести звук клика в режиме дыхания
}

// Остановка звука дыхания
function stopBreathingSound() {
    // Остановка звука дыхания
}
