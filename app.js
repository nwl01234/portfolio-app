const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();
tg.setHeaderColor('#000000');
tg.setBackgroundColor('#000000');

// State
let cart = [];
let selectedPayment = 'crypto';

// Navigation & Demo Logic
function openDemo(type) {
    document.getElementById('main-view').classList.remove('active');
    
    // Hide all demos
    document.querySelectorAll('.demo-view').forEach(el => el.classList.remove('active'));
    
    // Show specific demo
    const demoId = `demo-${type}`;
    const demoEl = document.getElementById(demoId);
    if(demoEl) {
        demoEl.classList.add('active');
        tg.BackButton.show();
        tg.BackButton.onClick(closeDemo);
    }
}

function closeDemo() {
    document.querySelectorAll('.demo-view').forEach(el => el.classList.remove('active'));
    document.getElementById('main-view').classList.add('active');
    tg.BackButton.hide();
}

// Cart Logic
function addToCart(name, price) {
    cart.push({ name, price });
    updateCartUI();
    tg.HapticFeedback.notificationOccurred('success');
    
    // Animation effect
    const btn = event.target;
    const originalText = btn.innerText;
    btn.innerText = "ADDED";
    btn.style.background = "#00ff88";
    setTimeout(() => {
        btn.innerText = originalText;
        btn.style.background = "white";
    }, 1000);
}

function updateCartUI() {
    const count = document.getElementById('cart-count');
    count.innerText = cart.length;
    count.classList.remove('hidden');
    if(cart.length === 0) count.classList.add('hidden');
}

function openCart() {
    if(cart.length === 0) {
        tg.showAlert("Cart is empty");
        return;
    }
    const modal = document.getElementById('cart-modal');
    const itemsList = document.getElementById('cart-items');
    const totalEl = document.getElementById('total-price');
    
    itemsList.innerHTML = '';
    let total = 0;
    
    cart.forEach(item => {
        total += item.price;
        itemsList.innerHTML += `<li style="margin-bottom:10px; border-bottom:1px solid #333; padding-bottom:10px;">
            ${item.name} <span style="float:right; color:#00ff88">$${item.price}</span>
        </li>`;
    });
    
    totalEl.innerText = total;
    modal.style.display = 'flex';
}

function closeCart() {
    document.getElementById('cart-modal').style.display = 'none';
}

function selectPay(method) {
    selectedPayment = method;
    document.querySelectorAll('.pay-option').forEach(el => el.classList.remove('selected'));
    event.currentTarget.classList.add('selected');
}

// Checkout & Messaging
function processCheckout() {
    const total = cart.reduce((sum, item) => sum + item.price, 0);
    const itemsNames = cart.map(i => i.name).join(', ');
    
    const message = `
🔥 NEW ORDER
----------------
📦 Items: ${itemsNames}
💰 Total: $${total}
💳 Method: ${selectedPayment.toUpperCase()}
----------------
Waiting for payment address...
    `;
    
    // Закрываем WebApp и отправляем данные в бот
    tg.sendData(JSON.stringify({
        type: 'order',
        items: itemsNames,
        total: total,
        payment: selectedPayment
    }));
    
    // Или открываем личку для оплаты (если WebApp не закрылся)
    tg.close();
}

function openSupport() {
    // ЗАМЕНИ НА СВОЙ ЮЗЕРНЕЙМ!
    const username = "nwl228"; 
    tg.openTelegramLink(`https://t.me/${username}?start=support_request`);
}

// Filter Logic
function filterServices(category) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    
    document.querySelectorAll('.service-card').forEach(card => {
        if(category === 'all' || card.dataset.category === category) {
            card.style.display = 'block';
        } else {
            card.style.display = 'none';
        }
    });
}