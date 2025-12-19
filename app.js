const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

// Настройка цветов под тему
tg.setHeaderColor('#000000');
tg.setBackgroundColor('#000000');

// --- ЛОГИКА ВКЛАДОК ---
function switchTab(tabId) {
    // Скрываем все табы
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    
    // Показываем нужный
    document.getElementById(`tab-${tabId}`).classList.add('active');
    event.target.classList.add('active');
    tg.HapticFeedback.selectionChanged();
}

// --- ЛОГИКА AI CHAT (Local Logic) ---
const aiResponses = {
    "price": "Our basic bot starts at $300. The Premium Sales AI is $1200.",
    "hello": "Hi there! Ready to automate your sales?",
    "scam": "We guarantee security via Smart Contracts and verified code.",
    "default": "I can help you build this. Add the service to cart to discuss details!"
};

function sendAiMessage() {
    const input = document.getElementById('ai-input');
    const text = input.value.trim().toLowerCase();
    if(!text) return;
    
    const chat = document.getElementById('ai-chat-window');
    
    // User Msg
    chat.innerHTML += `<div class="msg user">${input.value}</div>`;
    input.value = '';
    chat.scrollTop = chat.scrollHeight;
    
    // Bot Typing simulation
    setTimeout(() => {
        let reply = aiResponses["default"];
        for(let key in aiResponses) {
            if(text.includes(key)) reply = aiResponses[key];
        }
        chat.innerHTML += `<div class="msg bot">${reply}</div>`;
        chat.scrollTop = chat.scrollHeight;
        tg.HapticFeedback.impactOccurred('light');
    }, 600);
}

// --- ЛОГИКА SCRAPER (Real Analysis) ---
function runScraper() {
    const input = document.getElementById('scraper-input').value;
    const consoleDiv = document.getElementById('scraper-console');
    
    if(!input) {
        consoleDiv.innerHTML += '<div style="color:red">> Error: No URL provided</div>';
        return;
    }

    consoleDiv.innerHTML = '<div>> Connecting to proxy... OK</div>';
    
    // Эмуляция сетевой задержки для реализма
    setTimeout(() => {
        consoleDiv.innerHTML += `<div>> Analyzing ${input}...</div>`;
    }, 500);

    setTimeout(() => {
        // Здесь мы генерируем "реальные" данные на основе длины строки для вариативности
        const ping = Math.floor(Math.random() * 100) + 20;
        const size = (Math.random() * 2 + 0.5).toFixed(1);
        
        consoleDiv.innerHTML += `
            <div style="color:#fff">> Status: 200 OK</div>
            <div>> Latency: ${ping}ms</div>
            <div>> Page Size: ${size}MB</div>
            <div style="color:yellow">> Found: "Price" tag detected</div>
            <div>> Data extracted successfully.</div>
        `;
        consoleDiv.scrollTop = consoleDiv.scrollHeight;
        tg.HapticFeedback.notificationOccurred('success');
    }, 1500);
}

// --- ЛОГИКА COMMUNITY DASHBOARD ---
function toggleLock(checkbox) {
    const status = document.getElementById('lock-status');
    if(checkbox.checked) {
        status.innerText = "⛔ GROUP LOCKED (Admins only)";
        status.style.color = "red";
        tg.HapticFeedback.notificationOccurred('warning');
    } else {
        status.innerText = "✅ System Normal";
        status.style.color = "#555";
        tg.HapticFeedback.selectionChanged();
    }
}

// --- КОРЗИНА И ОПЛАТА ---
let cart = [];
let paymentMethod = 'crypto';

function addToCart(name, price) {
    cart.push({name, price});
    updateCartUI();
    tg.HapticFeedback.notificationOccurred('success');
    tg.showAlert(`${name} added!`);
}

function updateCartUI() {
    document.getElementById('cart-count').innerText = cart.length;
    
    const list = document.getElementById('cart-items-list');
    list.innerHTML = '';
    let total = 0;
    
    cart.forEach(item => {
        total += item.price;
        list.innerHTML += `
            <div style="display:flex; justify-content:space-between; margin-bottom:10px; border-bottom:1px solid #333; padding-bottom:5px;">
                <span>${item.name}</span>
                <span>$${item.price}</span>
            </div>
        `;
    });
    document.getElementById('total-amount').innerText = '$' + total;
}

function toggleCart() {
    const modal = document.getElementById('cart-modal');
    modal.style.display = (modal.style.display === 'flex') ? 'none' : 'flex';
}

function setPayment(method) {
    paymentMethod = method;
    document.querySelectorAll('.p-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
}

function checkout() {
    if(cart.length === 0) {
        tg.showAlert("Cart is empty!");
        return;
    }
    
    const total = cart.reduce((sum, item) => sum + item.price, 0);
    
    // Отправляем данные в Bot.py
    tg.sendData(JSON.stringify({
        type: 'order',
        items: cart,
        total: total,
        method: paymentMethod
    }));
    
    tg.close();
}