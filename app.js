const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();
tg.setHeaderColor('#0a0a0f');
tg.setBackgroundColor('#0a0a0f');

// --- DATA ---
const services = {
    ai: {
        title: "AI Automation",
        basic: { price: 300, features: ["Simple Menu Bot", "Auto-Replies", "Admin Panel", "24h Delivery"] },
        premium: { price: 1200, features: ["ChatGPT Integration", "Learns Your Files", "Human Handoff", "Analytics Dashboard"] }
    },
    scraper: {
        title: "Data Systems",
        basic: { price: 250, features: ["One-time Scrape", "Excel/CSV Export", "Up to 1000 items"] },
        premium: { price: 900, features: ["Real-time Monitoring", "Instant Telegram Alerts", "Anti-Detect System", "Competitor Tracking"] }
    },
    community: {
        title: "Community",
        basic: { price: 200, features: ["Welcome Bot", "Anti-Spam Filter", "Rules Enforcement"] },
        premium: { price: 800, features: ["Paid Subscriptions (Crypto)", "User Levels & XP", "Private Groups Access", "Referral System"] }
    }
};

let cart = [];
let currentService = 'ai';
let paymentMethod = 'crypto';

// --- NAVIGATION ---
function openService(type) {
    currentService = type;
    const s = services[type];
    
    // Fill UI
    document.getElementById('detail-title').innerText = s.title;
    
    // Basic
    document.getElementById('price-basic').innerText = '$' + s.basic.price;
    document.getElementById('features-basic').innerHTML = s.basic.features.map(f => `<li>${f}</li>`).join('');
    
    // Premium
    document.getElementById('price-premium').innerText = '$' + s.premium.price;
    document.getElementById('features-premium').innerHTML = s.premium.features.map(f => `<li>${f}</li>`).join('');
    
    // Update Buttons
    document.querySelector('.tier-card.basic .buy-btn').onclick = () => addToCart(s.title + ' (Starter)', s.basic.price);
    document.querySelector('.tier-card.premium .buy-btn').onclick = () => addToCart(s.title + ' (Enterprise)', s.premium.price);

    // Switch View
    document.getElementById('view-home').classList.remove('active');
    document.getElementById('view-details').classList.add('active');
    tg.BackButton.show();
    tg.BackButton.onClick(goHome);
}

function goHome() {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById('view-home').classList.add('active');
    tg.BackButton.hide();
}

// --- DEMO SYSTEM (SIMULATION) ---
function runDemo(tier) {
    const screen = document.getElementById('demo-screen');
    document.getElementById('view-demo').classList.add('active');
    screen.innerHTML = '<div style="color:#666; text-align:center; margin-top:50%;">Connecting to Demo Server...</div>';
    
    setTimeout(() => {
        screen.innerHTML = '';
        if(currentService === 'ai') startChatDemo(tier, screen);
        else if(currentService === 'scraper') startTerminalDemo(tier, screen);
        else startCommDemo(tier, screen);
    }, 1000);
}

function closeDemo() {
    document.getElementById('view-demo').classList.remove('active');
}

// Helper for chat demo
async function typeMsg(container, text, isBot = true) {
    const div = document.createElement('div');
    div.className = `msg ${isBot ? 'bot' : 'user'}`;
    div.innerText = text;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    if(isBot) tg.HapticFeedback.impactOccurred('light');
    await new Promise(r => setTimeout(r, 1000));
}

async function startChatDemo(tier, container) {
    await typeMsg(container, "Hello! How can I help you?", true);
    await new Promise(r => setTimeout(r, 800));
    await typeMsg(container, "Do you have prices?", false);
    
    if(tier === 'basic') {
        // Simple logic
        await typeMsg(container, "Here is our price list:\n1. Audit - $100\n2. Consult - $200", true);
    } else {
        // AI logic
        await typeMsg(container, "Certainly! Based on your needs, I recommend the Pro Plan ($200). It includes full analytics. Would you like to schedule a call?", true);
    }
}

async function startTerminalDemo(tier, container) {
    container.style.color = '#0f0';
    container.innerHTML = '<div>> Init_Sequence... OK</div>';
    await new Promise(r => setTimeout(r, 500));
    container.innerHTML += '<div>> Target: Amazon.com</div>';
    
    if(tier === 'basic') {
        container.innerHTML += '<div>> Scrape started...</div>';
        setTimeout(() => container.innerHTML += '<div>> DONE. Exported 50 rows to Excel.</div>', 1000);
    } else {
        container.innerHTML += '<div>> MONITORING MODE ACTIVE (24/7)</div>';
        setInterval(() => {
            container.innerHTML += `<div style="color:yellow">> Change detected! Price drop -15%</div>`;
            container.scrollTop = container.scrollHeight;
            tg.HapticFeedback.notificationOccurred('warning');
        }, 1500);
    }
}

function startCommDemo(tier, container) {
    // Similar logic for community...
    typeMsg(container, "User @john_doe joined.", true);
    if(tier === 'premium') typeMsg(container, "⚡ @john_doe paid 50 USDT via CryptoBot. Access Granted.", true);
}

// --- CART & CHECKOUT ---
function addToCart(name, price) {
    cart.push({name, price});
    document.getElementById('cart-badge').innerText = cart.length;
    document.getElementById('cart-badge').style.display = 'block';
    tg.HapticFeedback.notificationOccurred('success');
    tg.showAlert('Added to cart!');
    goHome();
}

function toggleCart() {
    const modal = document.getElementById('cart-modal');
    if(modal.style.display === 'flex') modal.style.display = 'none';
    else {
        renderCart();
        modal.style.display = 'flex';
    }
}

function renderCart() {
    const list = document.getElementById('cart-items');
    list.innerHTML = '';
    let total = 0;
    cart.forEach((item, i) => {
        total += item.price;
        list.innerHTML += `<div class="cart-item"><span>${item.name}</span><span>$${item.price}</span></div>`;
    });
    document.getElementById('cart-total').innerText = '$' + total;
}

function selectPay(method) {
    paymentMethod = method;
    document.querySelectorAll('.pay-btn').forEach(b => b.classList.remove('active'));
    event.currentTarget.classList.add('active');
}

function checkout() {
    if(cart.length === 0) return;
    
    const data = {
        type: 'order',
        cart: cart,
        total: document.getElementById('cart-total').innerText,
        method: paymentMethod
    };
    
    tg.sendData(JSON.stringify(data));
}

// Particles Init
document.addEventListener('DOMContentLoaded', () => {
    particlesJS('particles-js', {
        particles: { number: { value: 30 }, color: { value: "#ffffff" }, opacity: { value: 0.1 }, size: { value: 3 }, line_linked: { enable: true, opacity: 0.05 } }
    });
});