// Ждем загрузки Telegram WebApp
const tg = window.Telegram.WebApp;

// Сообщаем Телеграму, что приложение готово
tg.ready();
// Растягиваем на весь экран
tg.expand();

// Настраиваем цвета шапки под нашу тему
tg.setHeaderColor('#050507'); 
tg.setBackgroundColor('#050507');

// Функция плавного скролла к секциям
function scrollToId(id) {
    const element = document.getElementById(id);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
        
        // Вибрация при нажатии (только на мобильных)
        if(tg.HapticFeedback) {
            tg.HapticFeedback.impactOccurred('light');
        }
        
        // Меняем активную кнопку в меню
        document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
        event.target.classList.add('active');
    }
}

// Функция открытия лички с тобой для заказа
function openChat(topic) {
    // Вибрация для тактильного отклика
    if(tg.HapticFeedback) {
        tg.HapticFeedback.notificationOccurred('success');
    }
    
    // Формируем текст сообщения
    // ВАЖНО: Замени 'твоя_ссылка' на твой реальный юзернейм, например 'notwarlove' (без @)
    const username = "NWL01234"; // <-- ВПИШИ СЮДА СВОЙ ЮЗЕРНЕЙМ БЕЗ СОБАКИ
    const text = encodeURIComponent(`Hi! I'm interested in: ${topic}`);
    
    // Используем встроенный метод Telegram для открытия ссылки
    tg.openTelegramLink(`https://t.me/${username}?text=${text}`);
}

// Инициализация частиц на фоне (красивый эффект)
document.addEventListener('DOMContentLoaded', function() {
    if(window.particlesJS) {
        particlesJS('particles-js', {
            "particles": {
                "number": { "value": 40 },
                "color": { "value": "#ffffff" },
                "opacity": { "value": 0.3, "random": true },
                "size": { "value": 2, "random": true },
                "line_linked": { "enable": true, "distance": 150, "color": "#ffffff", "opacity": 0.1, "width": 1 },
                "move": { "enable": true, "speed": 1 }
            },
            "interactivity": { "events": { "onhover": { "enable": false }, "onclick": { "enable": false } } }
        });
    }
});