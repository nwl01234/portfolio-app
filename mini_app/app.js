// Инициализация Telegram WebApp
const tg = window.Telegram.WebApp;

// Сообщаем Телеграму, что приложение готово и его можно развернуть на весь экран
tg.ready();
tg.expand(); 

// Настраиваем цвета хедера под тему пользователя
tg.setHeaderColor('#0f172a'); 

// Данные для демо-кейсов
const demoContent = {
    shop: `
        <div style="font-size: 50px; color: #6366f1; margin-bottom: 10px;"><i class="fa-solid fa-basket-shopping"></i></div>
        <h3>E-commerce Bot</h3>
        <p style="text-align: left; margin-top: 15px; font-size: 14px; color: #cbd5e1;">
            ✅ Product Catalog (Grid/List)<br>
            ✅ Cart & Checkout Logic<br>
            ✅ Stripe/PayPal Payments<br>
            ✅ Order Tracking
        </p>
        <button class="btn-main" style="width:100%; margin-top: 20px; background: #6366f1; color: white;">Add to Cart (Demo)</button>
    `,
    analytics: `
        <h3>Live Channel Analytics</h3>
        <div class="bar-chart">
            <div class="bar" style="height: 40%"></div>
            <div class="bar" style="height: 70%"></div>
            <div class="bar" style="height: 50%"></div>
            <div class="bar" style="height: 90%"></div>
            <div class="bar" style="height: 60%"></div>
        </div>
        <p style="margin-top: 15px;">+127% Subscriber Growth</p>
    `,
    ai: `
        <div style="background: #1e293b; padding: 10px; border-radius: 10px; margin-bottom: 10px; text-align: left;">
            <small style="color: #6366f1;">User:</small><br> Write a Python script.
        </div>
        <div style="background: #334155; padding: 10px; border-radius: 10px; text-align: left;">
            <small style="color: #10b981;">AI Bot:</small><br> Sure! Here is your code...
        </div>
        <p style="margin-top: 15px; font-size: 13px;">Integrated with OpenAI API (GPT-4).</p>
    `
};

// Функция открытия модального окна
function openDemo(type) {
    const modal = document.getElementById('demoModal');
    const title = document.getElementById('modalTitle');
    const body = document.getElementById('modalBody');

    // Вибрация (Haptic Feedback) для тактильного ощущения
    tg.HapticFeedback.impactOccurred('light');

    title.innerText = type.charAt(0).toUpperCase() + type.slice(1) + " Demo";
    body.innerHTML = demoContent[type];
    
    modal.style.display = 'flex';
}

// Закрытие модального окна
function closeModal() {
    document.getElementById('demoModal').style.display = 'none';
}

// Обработка кнопки "Contact Me"
function openContact() {
    tg.HapticFeedback.impactOccurred('medium');
    // Открывает диалог с тобой (замени username)
    // Либо просто закрывает окно, чтобы вернуться в чат
    tg.close(); 
}

// Обработка кнопки "Pricing"
function openPricing() {
    tg.showPopup({
        title: 'Development Rates',
        message: 'Basic Bot: $300+\nMini App: $800+\nFull SaaS: $1500+',
        buttons: [{type: 'ok'}]
    });
}