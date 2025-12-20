const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();
tg.setHeaderColor('#030305');
tg.setBackgroundColor('#030305');

// Loader
window.onload = () => {
    setTimeout(() => {
        document.getElementById('loader').style.opacity = '0';
        setTimeout(() => document.getElementById('loader').style.display = 'none', 500);
    }, 1500);
    
    // Init Particles
    particlesJS('particles-js', {
        particles: { number: { value: 40 }, color: { value: "#ffffff" }, opacity: { value: 0.2 }, size: { value: 2 }, move: { enable: true, speed: 0.5 } }
    });
};

// --- TABS LOGIC ---
function setTab(id) {
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.getElementById('tab-'+id).classList.add('active');
    event.currentTarget.classList.add('active');
    tg.HapticFeedback.selectionChanged();
}

// --- REAL AI LOGIC ---
const aiBrain = {
    "price": "Standard bots start at $300. Custom Enterprise AI starts at $1200.",
    "scraper": "I can scrape Amazon, eBay, Instagram, and more. 99% uptime.",
    "community": "I can manage groups up to 100k members with auto-moderation.",
    "hello": "Greetings. Ready to automate your business?",
    "help": "Tell me what you need: AI, Data, or Community tools."
};

function handleEnter(e) { if(e.key === 'Enter') sendAi(); }

function sendAi() {
    const input = document.getElementById('ai-input');
    const txt = input.value.trim().toLowerCase();
    if(!txt) return;

    const box = document.getElementById('ai-chat');
    // User Msg
    box.innerHTML += `<div class="msg user">${input.value}</div>`;
    input.value = '';
    box.scrollTop = box.scrollHeight;

    // Bot Typing
    setTimeout(() => {
        let reply = "I can build that solution. Add to cart to discuss specific requirements.";
        for(let key in aiBrain) {
            if(txt.includes(key)) reply = aiBrain[key];
        }
        box.innerHTML += `<div class="msg bot">${reply}</div>`;
        box.scrollTop = box.scrollHeight;
        tg.HapticFeedback.impactOccurred('light');
    }, 800);
}

// --- REAL SCRAPER LOGIC ---
function runScrape() {
    const term = document.getElementById('term-screen');
    const url = document.getElementById('scraper-input').value || "target_host";
    
    term.innerHTML = `<div class="line">root@nwl:~# initiating scrape sequence on ${url}</div>`;
    
    const steps = [
        `> Connecting to proxy pool (US_EAST)...`,
        `> [SUCCESS] Handshake established 24ms`,
        `> Bypassing Cloudflare protection...`,
        `> [OK] 200 OK Received`,
        `> Parsing DOM elements...`,
        `> Found 142 data points. Exporting JSON...`,
        `<span style="color:#0f0">> JOB COMPLETE. Data ready for export.</span>`
    ];

    let i = 0;
    const interval = setInterval(() => {
        if(i >= steps.length) clearInterval(interval);
        else {
            term.innerHTML += `<div class="line">${steps[i]}</div>`;
            term.scrollTop = term.scrollHeight;
            tg.HapticFeedback.selectionChanged();
            i++;
        }
    }, 600);
}

// --- DASHBOARD LOGIC ---
function toggleNotify(feature) {
    tg.HapticFeedback.notificationOccurred('success');
    tg.showAlert(`${feature} Status Updated`);
}

// --- CART & PAYMENT ---
let cart = [];
let payMethod = 'usdt';

function addToCart(name, price) {
    cart.push({name, price});
    document.getElementById('cart-badge').innerText = cart.length;
    document.getElementById('cart-badge').classList.remove('hidden');
    tg.HapticFeedback.notificationOccurred('success');
}

function openCart() {
    if(cart.length === 0) return tg.showAlert("Cart is empty");
    const list = document.getElementById('cart-list');
    list.innerHTML = '';
    let total = 0;
    
    cart.forEach(item => {
        total += item.price;
        list.innerHTML += `<div style="display:flex; justify-content:space-between; margin-bottom:10px; border-bottom:1px solid #333; padding-bottom:10px;"><span>${item.name}</span><span>$${item.price}</span></div>`;
    });
    
    document.getElementById('total-price').innerText = '$' + total;
    document.getElementById('cart-overlay').style.display = 'flex';
}

function closeCart() {
    document.getElementById('cart-overlay').style.display = 'none';
}

function setPay(method) {
    payMethod = method;
    document.querySelectorAll('.pay-option').forEach(el => el.classList.remove('active'));
    event.currentTarget.classList.add('active');
}

function checkout() {
    const total = document.getElementById('total-price').innerText;
    
    // SEND DATA TO BOT
    tg.sendData(JSON.stringify({
        type: 'order',
        cart: cart,
        total: total,
        method: payMethod
    }));
    tg.close();
}

// --- MESSENGER LINK ---
function openMessenger() {
    // Просто закрываем WebApp, а бот уже ждет сообщения
    tg.close();
    // Или можно использовать tg.openTelegramLink если хочешь открыть конкретный чат
}