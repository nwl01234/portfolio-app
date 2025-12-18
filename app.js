const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();
tg.setHeaderColor('#000000');
tg.setBackgroundColor('#000000');
tg.enableClosingConfirmation();

// State
let cart = [];
let selectedPayment = 'crypto';
let chatMessages = [];

// DOM Elements
const cartCountEl = document.getElementById('cart-count');
const cartItemsEl = document.getElementById('cart-items');
const emptyCartEl = document.getElementById('empty-cart');
const subtotalEl = document.getElementById('subtotal-price');
const feeEl = document.getElementById('fee-price');
const totalEl = document.getElementById('total-price');
const checkoutBtn = document.getElementById('checkout-btn');
const messageInput = document.getElementById('message-input');
const chatMessagesEl = document.getElementById('chat-messages');

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    loadCart();
    updateCartUI();
    setupEventListeners();
});

// Cart Functions
function loadCart() {
    const saved = localStorage.getItem('portfolio_cart');
    if (saved) {
        try {
            cart = JSON.parse(saved);
        } catch (e) {
            cart = [];
        }
    }
}

function saveCart() {
    localStorage.setItem('portfolio_cart', JSON.stringify(cart));
}

function addToCart(name, price) {
    const existing = cart.find(item => item.name === name);
    if (existing) {
        existing.quantity += 1;
    } else {
        cart.push({
            name: name,
            price: price,
            quantity: 1,
            id: Date.now().toString()
        });
    }
    
    saveCart();
    updateCartUI();
    
    // Haptic feedback
    tg.HapticFeedback.impactOccurred('light');
    
    // Button animation
    const btn = event.target;
    const originalText = btn.innerText;
    const originalBg = btn.style.background;
    
    btn.innerText = "✓ ADDED";
    btn.style.background = "var(--accent)";
    btn.style.color = "black";
    
    setTimeout(() => {
        btn.innerText = originalText;
        btn.style.background = originalBg;
        btn.style.color = "";
    }, 1500);
}

function removeFromCart(itemId) {
    const index = cart.findIndex(item => item.id === itemId);
    if (index !== -1) {
        cart.splice(index, 1);
        saveCart();
        updateCartUI();
        tg.HapticFeedback.impactOccurred('medium');
    }
}

function updateCartUI() {
    // Update count
    const totalItems = cart.reduce((sum, item) => sum + item.quantity, 0);
    cartCountEl.innerText = totalItems;
    
    if (totalItems > 0) {
        cartCountEl.classList.remove('hidden');
    } else {
        cartCountEl.classList.add('hidden');
    }
    
    // Update modal items
    if (cartItemsEl) {
        cartItemsEl.innerHTML = '';
        
        if (cart.length === 0) {
            emptyCartEl.style.display = 'block';
            checkoutBtn.disabled = true;
        } else {
            emptyCartEl.style.display = 'none';
            checkoutBtn.disabled = false;
            
            cart.forEach(item => {
                const li = document.createElement('li');
                li.innerHTML = `
                    <div class="item-name">${item.name} × ${item.quantity}</div>
                    <div class="item-price">$${item.price * item.quantity}</div>
                    <button class="item-remove" onclick="removeFromCart('${item.id}')">
                        <i class="fas fa-times"></i>
                    </button>
                `;
                cartItemsEl.appendChild(li);
            });
            
            // Calculate prices
            const subtotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
            const fee = subtotal * 0.02; // 2% fee
            const total = subtotal + fee;
            
            subtotalEl.innerText = subtotal.toFixed(0);
            feeEl.innerText = fee.toFixed(0);
            totalEl.innerText = total.toFixed(0);
        }
    }
}

// Payment Functions
function selectPayment(method) {
    selectedPayment = method;
    
    // Update UI
    document.querySelectorAll('.pay-option').forEach(el => {
        el.classList.remove('selected');
    });
    
    event.currentTarget.classList.add('selected');
    
    // Update fee based on payment method
    if (method === 'crypto') {
        // 2% discount for crypto
        const subtotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
        const fee = subtotal * 0.02;
        const total = subtotal + fee;
        
        feeEl.innerText = fee.toFixed(0);
        totalEl.innerText = total.toFixed(0);
    } else {
        // Regular fee for wallet
        const subtotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
        const fee = subtotal * 0.03; // 3% for wallet
        const total = subtotal + fee;
        
        feeEl.innerText = fee.toFixed(0);
        totalEl.innerText = total.toFixed(0);
    }
}

// Checkout Process
function processCheckout() {
    if (cart.length === 0) {
        tg.showAlert('Your cart is empty');
        return;
    }
    
    const subtotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    const fee = selectedPayment === 'crypto' ? subtotal * 0.02 : subtotal * 0.03;
    const total = subtotal + fee;
    
    // Prepare order data
    const orderData = {
        type: 'order',
        items: cart.map(item => `${item.name} (x${item.quantity})`).join(', '),
        subtotal: subtotal,
        fee: fee.toFixed(0),
        total: total.toFixed(0),
        payment: selectedPayment,
        timestamp: new Date().toISOString(),
        customer: {
            id: tg.initDataUnsafe?.user?.id || 'unknown',
            username: tg.initDataUnsafe?.user?.username || 'unknown'
        }
    };
    
    // Send to Telegram bot
    tg.sendData(JSON.stringify(orderData));
    
    // Show success message
    showSuccessModal();
    
    // Clear cart
    cart = [];
    saveCart();
    updateCartUI();
    
    // Close cart modal
    closeCart();
    
    // Vibrate
    tg.HapticFeedback.notificationOccurred('success');
}

// Demo Navigation
function openDemo(type) {
    // Hide all views
    document.querySelectorAll('.view').forEach(el => {
        el.classList.remove('active');
    });
    
    // Show specific demo
    const demoId = `demo-${type}`;
    const demoEl = document.getElementById(demoId);
    
    if (demoEl) {
        demoEl.classList.add('active');
        tg.BackButton.show();
        tg.BackButton.onClick(closeDemo);
    }
}

function closeDemo() {
    document.querySelectorAll('.demo-view').forEach(el => {
        el.classList.remove('active');
    });
    
    document.getElementById('main-view').classList.add('active');
    tg.BackButton.hide();
}

// Cart Modal
function openCart() {
    const modal = document.getElementById('cart-modal');
    updateCartUI();
    modal.style.display = 'flex';
    tg.HapticFeedback.impactOccurred('soft');
}

function closeCart() {
    document.getElementById('cart-modal').style.display = 'none';
}

// Success Modal
function showSuccessModal() {
    const modal = document.getElementById('success-modal');
    modal.style.display = 'flex';
}

function closeSuccess() {
    document.getElementById('success-modal').style.display = 'none';
}

// Messenger Functions
function openMessenger() {
    const modal = document.getElementById('messenger-modal');
    modal.style.display = 'flex';
    tg.HapticFeedback.impactOccurred('soft');
    
    // Focus on input
    setTimeout(() => {
        if (messageInput) {
            messageInput.focus();
        }
    }, 300);
}

function closeMessenger() {
    document.getElementById('messenger-modal').style.display = 'none';
}

function sendMessage() {
    const text = messageInput.value.trim();
    if (!text) return;
    
    // Add user message
    addChatMessage('user', text);
    
    // Clear input
    messageInput.value = '';
    
    // Simulate bot reply after delay
    setTimeout(() => {
        const replies = [
            "Thanks for your message! I'll get back to you shortly.",
            "I've received your question. Our team usually responds within 1 hour.",
            "Great question! Let me check the details and I'll reply soon.",
            "Thanks for reaching out. I'm here to help with any questions."
        ];
        
        const randomReply = replies[Math.floor(Math.random() * replies.length)];
        addChatMessage('bot', randomReply);
    }, 1000);
    
    // Send message data to bot (for actual support system)
    const messageData = {
        type: 'support_message',
        text: text,
        user: tg.initDataUnsafe?.user || {},
        timestamp: new Date().toISOString()
    };
    
    tg.sendData(JSON.stringify(messageData));
    
    tg.HapticFeedback.impactOccurred('light');
}

function addChatMessage(sender, text) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${sender}`;
    
    const senderName = sender === 'bot' ? 'Support' : 'You';
    messageDiv.innerHTML = `
        <div class="message-content">
            <strong>${senderName}</strong>
            <p>${text}</p>
        </div>
    `;
    
    chatMessagesEl.appendChild(messageDiv);
    
    // Scroll to bottom
    const container = document.querySelector('.chat-container');
    container.scrollTop = container.scrollHeight;
}

// Service Filtering
function filterServices(category) {
    // Update active tab
    document.querySelectorAll('.tab-btn').forEach(b => {
        b.classList.remove('active');
    });
    event.target.classList.add('active');
    
    // Filter cards
    document.querySelectorAll('.service-card').forEach(card => {
        if (category === 'all') {
            card.style.display = 'block';
        } else if (category === 'premium') {
            card.style.display = card.classList.contains('premium') ? 'block' : 'none';
        } else if (category === 'standard') {
            card.style.display = card.classList.contains('standard') ? 'block' : 'none';
        } else {
            // Filter by data-category attribute
            const categories = card.dataset.category.split(' ');
            card.style.display = categories.includes(category) ? 'block' : 'none';
        }
        
        // Add animation
        card.style.animation = 'none';
        setTimeout(() => {
            card.style.animation = 'fadeIn 0.5s';
        }, 10);
    });
}

// Event Listeners
function setupEventListeners() {
    // Enter key in messenger
    if (messageInput) {
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    }
    
    // Close modals on outside click
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    });
}

// Initialize chat with welcome message
setTimeout(() => {
    if (chatMessagesEl.children.length === 0) {
        addChatMessage('bot', 'Welcome! How can I help you today?');
    }
}, 500);