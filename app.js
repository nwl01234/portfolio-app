// ===== INITIALIZATION =====
const tg = window.Telegram?.WebApp;

if (tg) {
    tg.ready();
    tg.expand();
    tg.setHeaderColor('#0a0a0f');
    tg.setBackgroundColor('#0a0a0f');
}

// ===== STATE MANAGEMENT =====
const state = {
    theme: 'dark',
    language: 'en',
    cart: [],
    demoActive: false
};

// ===== LANGUAGE DICTIONARY =====
const translations = {
    en: {
        // Header
        "logo": "TelegramDev",
        "themeToggle": "Theme",
        "langToggle": "Русский",
        
        // Hero
        "badge": "TOP 1% TELEGRAM DEVELOPER",
        "titleLine1": "Enterprise-Grade",
        "titleLine2": "Telegram Solutions",
        "subtitle": "Premium bots that drive revenue & automate growth for US businesses since 2022",
        "clients": "Clients",
        "revenue": "Revenue Generated",
        "uptime": "Uptime",
        
        // Navigation
        "navAi": "AI Support",
        "navEcom": "E-commerce",
        "navBooking": "Booking",
        "navMembership": "Membership",
        "navFeedback": "Feedback",
        "navCustom": "Custom",
        
        // AI Section
        "aiTitle": "AI Customer Support",
        "aiSubtitle": "24/7 intelligent support with GPT-4 integration",
        "basicTag": "Quick Start",
        "basicPrice": "$299",
        "premiumTag": "Enterprise",
        "premiumPrice": "$999+",
        
        // E-commerce Section
        "ecomTitle": "E-commerce Store",
        "ecomSubtitle": "Complete shopping experience inside Telegram",
        "starterTag": "Starter",
        "starterPrice": "$499",
        "advancedTag": "Advanced",
        "advancedPrice": "$1,499+",
        
        // Buttons
        "tryDemo": "Try Demo",
        "launchDemo": "Launch Demo",
        "contactMe": "Contact Me",
        "pricing": "Pricing",
        "bookCall": "Book Call",
        
        // CTA
        "ctaTitle": "Ready to Build Your Solution?",
        "ctaSubtitle": "Book a free 30-minute strategy call",
        
        // Footer
        "footer": "© 2023 Telegram Bot Developer. All rights reserved."
    },
    ru: {
        // Header
        "logo": "TelegramDev",
        "themeToggle": "Тема",
        "langToggle": "English",
        
        // Hero
        "badge": "ТОП 1% РАЗРАБОТЧИКОВ TELEGRAM",
        "titleLine1": "Корпоративные",
        "titleLine2": "Решения для Telegram",
        "subtitle": "Премиум боты, которые увеличивают доход и автоматизируют рост для бизнеса США с 2022",
        "clients": "Клиентов",
        "revenue": "Доход Сгенерирован",
        "uptime": "Аптайм",
        
        // Navigation
        "navAi": "AI Поддержка",
        "navEcom": "E-commerce",
        "navBooking": "Бронирование",
        "navMembership": "Подписки",
        "navFeedback": "Отзывы",
        "navCustom": "Кастом",
        
        // AI Section
        "aiTitle": "AI Поддержка Клиентов",
        "aiSubtitle": "Круглосуточная интеллектуальная поддержка с GPT-4",
        "basicTag": "Базовый",
        "basicPrice": "$299",
        "premiumTag": "Предприятие",
        "premiumPrice": "$999+",
        
        // E-commerce Section
        "ecomTitle": "Интернет-магазин",
        "ecomSubtitle": "Полноценный шоппинг внутри Telegram",
        "starterTag": "Стартовый",
        "starterPrice": "$499",
        "advancedTag": "Продвинутый",
        "advancedPrice": "$1,499+",
        
        // Buttons
        "tryDemo": "Попробовать Демо",
        "launchDemo": "Запустить Демо",
        "contactMe": "Написать Мне",
        "pricing": "Цены",
        "bookCall": "Записать Звонок",
        
        // CTA
        "ctaTitle": "Готовы Создать Решение?",
        "ctaSubtitle": "Забронируйте бесплатную 30-минутную консультацию",
        
        // Footer
        "footer": "© 2023 Разработчик Telegram Ботов. Все права защищены."
    }
};

// ===== THEME & LANGUAGE CONTROLS =====
function initControls() {
    // Theme Toggle
    const themeBtn = document.getElementById('themeToggle');
    if (themeBtn) {
        themeBtn.addEventListener('click', toggleTheme);
    }
    
    // Language Toggle
    const langBtn = document.getElementById('langToggle');
    if (langBtn) {
        langBtn.addEventListener('click', toggleLanguage);
    }
    
    // Set initial theme
    document.documentElement.setAttribute('data-theme', state.theme);
    updateThemeButton();
}

function toggleTheme() {
    state.theme = state.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', state.theme);
    updateThemeButton();
    if (tg) tg.HapticFeedback.impactOccurred('light');
}

function updateThemeButton() {
    const btn = document.getElementById('themeToggle');
    if (btn) {
        btn.innerHTML = state.theme === 'dark' 
            ? '<i class="fas fa-sun"></i> Light'
            : '<i class="fas fa-moon"></i> Dark';
    }
}

function toggleLanguage() {
    state.language = state.language === 'en' ? 'ru' : 'en';
    applyTranslation();
    updateLanguageButton();
    if (tg) tg.HapticFeedback.impactOccurred('light');
}

function updateLanguageButton() {
    const btn = document.getElementById('langToggle');
    if (btn) {
        btn.textContent = state.language === 'en' ? 'Русский' : 'English';
    }
}

function applyTranslation() {
    const dict = translations[state.language];
    if (!dict) return;
    
    // Update all elements with data-i18n attribute
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (dict[key]) el.textContent = dict[key];
    });
    
    // Update placeholders
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        if (dict[key]) el.placeholder = dict[key];
    });
}

// ===== DEMO FUNCTIONS (исправленные) =====
function launchAIDemo(type) {
    if (state.demoActive) return;
    state.demoActive = true;
    
    if (tg) tg.HapticFeedback.impactOccurred('medium');
    
    const messages = type === 'basic' 
        ? [
            { role: 'user', text: "My order #4562 hasn't arrived" },
            { role: 'bot', text: "Checking your order status... ✅ Shipped on Dec 10\nEstimated delivery: Today\nTrack your package: [Live Tracking]" }
          ]
        : [
            { role: 'user', text: "Analyze our support metrics" },
            { role: 'bot', text: "📊 Analysis Complete:\n• Response Time: 4.2s (↓12%)\n• Satisfaction: 94% (↑8%)\n• Recommendation: Add Spanish support to capture 15% more users" }
          ];
    
    showDemoModal('AI Support Demo', messages, type);
    setTimeout(() => { state.demoActive = false; }, 1000);
}

function launchEcomDemo(type) {
    if (state.demoActive) return;
    state.demoActive = true;
    
    if (tg) tg.HapticFeedback.impactOccurred('light');
    
    const title = type === 'basic' ? 'E-commerce Demo' : 'Advanced Store Demo';
    const message = type === 'basic'
        ? "🛍️ Interactive store demo loaded!\n• Add to Cart functionality\n• Live price calculation\n• Checkout process simulation"
        : "🚀 Advanced features activated:\n• 1-Click Upsell engine\n• Dynamic pricing algorithms\n• Abandoned cart recovery system";
    
    showDemoModal(title, [{ role: 'system', text: message }], type);
    setTimeout(() => { state.demoActive = false; }, 1000);
}

function showDemoModal(title, messages, type) {
    // Create modal overlay
    const overlay = document.createElement('div');
    overlay.className = 'demo-overlay';
    overlay.style.cssText = `
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.8); backdrop-filter: blur(5px);
        display: flex; align-items: center; justify-content: center;
        z-index: 9999; animation: fadeIn 0.3s;
    `;
    
    // Create modal content
    const modal = document.createElement('div');
    modal.className = 'demo-modal';
    modal.style.cssText = `
        background: var(--bg-secondary); border-radius: 20px;
        padding: 30px; max-width: 400px; width: 90%;
        border: 2px solid ${type === 'premium' ? '#ffd166' : '#00d4ff'};
        position: relative; animation: slideIn 0.3s;
    `;
    
    // Close button
    const closeBtn = document.createElement('button');
    closeBtn.innerHTML = '&times;';
    closeBtn.style.cssText = `
        position: absolute; top: 15px; right: 20px;
        background: none; border: none; font-size: 28px;
        cursor: pointer; color: var(--text-secondary);
    `;
    closeBtn.onclick = () => document.body.removeChild(overlay);
    
    // Title
    const titleEl = document.createElement('h3');
    titleEl.textContent = title;
    titleEl.style.cssText = 'margin-bottom: 20px; text-align: center;';
    
    // Messages
    const messagesEl = document.createElement('div');
    messagesEl.style.cssText = 'display: flex; flex-direction: column; gap: 15px;';
    
    messages.forEach(msg => {
        const msgEl = document.createElement('div');
        msgEl.textContent = msg.text;
        msgEl.style.cssText = `
            padding: 15px; border-radius: 15px; white-space: pre-line;
            background: ${msg.role === 'user' ? 'rgba(0, 212, 255, 0.1)' : 'var(--bg-tertiary)'};
            border: 1px solid ${msg.role === 'user' ? 'rgba(0, 212, 255, 0.2)' : 'var(--border-color)'};
            align-self: ${msg.role === 'user' ? 'flex-start' : 'flex-end'};
            max-width: 85%;
        `;
        messagesEl.appendChild(msgEl);
    });
    
    // Assemble modal
    modal.appendChild(closeBtn);
    modal.appendChild(titleEl);
    modal.appendChild(messagesEl);
    overlay.appendChild(modal);
    document.body.appendChild(overlay);
    
    // Close on overlay click
    overlay.onclick = (e) => {
        if (e.target === overlay) document.body.removeChild(overlay);
    };
}

// ===== CONTACT FUNCTIONS =====
function contactTelegram() {
    if (tg) {
        tg.HapticFeedback.notificationOccurred('success');
        tg.openTelegramLink('https://t.me/yourusername');
    } else {
        window.open('https://t.me/yourusername', '_blank');
    }
}

function bookCall() {
    if (tg) {
        tg.HapticFeedback.impactOccurred('heavy');
        tg.showPopup({
            title: '📅 Schedule Strategy Call',
            message: 'Redirecting to calendar...',
            buttons: [{ type: 'default', text: 'Open Calendar', id: 'calendar' }]
        });
        
        tg.onEvent('popupButtonClicked', (data) => {
            if (data.button_id === 'calendar') {
                window.open('https://calendly.com/yourusername/30min', '_blank');
            }
        });
    } else {
        window.open('https://calendly.com/yourusername/30min', '_blank');
    }
}

// ===== INITIALIZATION =====
document.addEventListener('DOMContentLoaded', () => {
    initControls();
    applyTranslation();
    
    // Initialize all interactive elements
    document.querySelectorAll('.card-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    });
    
    // Smooth scroll for navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href')?.replace('#', '');
            if (targetId) {
                const target = document.getElementById(targetId);
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth' });
                }
            }
        });
    });
    
    console.log('Portfolio initialized successfully!');
});