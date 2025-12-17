// Initialize Telegram WebApp
const tg = window.Telegram.WebApp;
let isExpanded = false;

// Initialize app
function initApp() {
    tg.ready();
    tg.expand();
    tg.setHeaderColor('#0a0a0f');
    tg.setBackgroundColor('#0a0a0f');
    
    // Initialize particles
    particlesJS.load('particles-js', 'particles-config.json', function() {
        console.log('Particles loaded');
    });
    
    // Add scroll animations
    initScrollAnimations();
    
    // Initialize demos
    initDemos();
    
    // Track user interactions
    initAnalytics();
}

// Scroll animations
function initScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate__animated', 'animate__fadeInUp');
            }
        });
    }, observerOptions);
    
    // Observe all solution sections
    document.querySelectorAll('.solution-section').forEach(section => {
        observer.observe(section);
    });
}

// AI Demo System
function launchAIDemo(type) {
    tg.HapticFeedback.impactOccurred('medium');
    
    if (type === 'basic') {
        showAIChatDemo();
    } else {
        showAIAnalyticsDemo();
    }
}

function showAIChatDemo() {
    const messages = [
        { role: 'user', text: "What's your return policy?" },
        { role: 'bot', text: "We offer 30-day returns for all products. Do you need help with a specific return?" },
        { role: 'user', text: "Yes, order #7890" },
        { role: 'bot', text: "✅ Found your order. Return label generated! Track it here: [Tracking Link]" }
    ];
    
    showChatDemo('AI Support Demo', messages);
}

function showAIAnalyticsDemo() {
    tg.showPopup({
        title: '🤖 AI Analytics Dashboard',
        message: 'Processing customer data...',
        buttons: [{
            id: 'analyze',
            type: 'default',
            text: 'Run Analysis'
        }]
    });
    
    // Simulate AI processing
    setTimeout(() => {
        tg.showPopup({
            title: '📊 Analysis Complete',
            message: 'Opportunities found:\n\n• 42% cart abandonment rate\n• Upsell potential: $12K/month\n• Spanish support ROI: 180%',
            buttons: [{
                type: 'ok',
                text: 'View Full Report'
            }]
        });
    }, 1500);
}

// E-commerce Demo System
function launchEcomDemo(type) {
    tg.HapticFeedback.impactOccurred('light');
    
    if (type === 'basic') {
        showBasicStore();
    } else {
        showAdvancedStore();
    }
}

function showBasicStore() {
    const products = [
        { id: 1, name: "Premium Template", price: 49, color: "#4ECDC4" },
        { id: 2, name: "AI Assistant", price: 97, color: "#FF6B6B" },
        { id: 3, name: "Course Bundle", price: 199, color: "#9B5DE5" }
    ];
    
    showProductGrid(products);
}

function showAdvancedStore() {
    // Show live sales simulation
    let sales = 2847;
    const salesElement = document.querySelector('.analytics-value');
    
    // Animate sales counter
    const interval = setInterval(() => {
        sales += Math.floor(Math.random() * 100);
        salesElement.innerHTML = `$${sales.toLocaleString()} <span class="today">today</span>`;
    }, 2000);
    
    // Show upsell popup
    setTimeout(() => {
        tg.showPopup({
            title: '🚀 Smart Upsell Triggered',
            message: 'Based on user behavior, suggest:\n\n• Course Bundle (+$149)\n• Yearly Plan (+$299/yr)\n• Consulting (+$500)',
            buttons: [
                { id: 'accept', type: 'default', text: 'Add to Order' },
                { id: 'decline', type: 'destructive', text: 'Skip' }
            ]
        });
    }, 3000);
}

// Contact Functions
function contactWhatsApp() {
    tg.HapticFeedback.notificationOccurred('success');
    tg.openLink('https://wa.me/1234567890?text=Hi!%20I%20saw%20your%20Telegram%20portfolio%20and%20want%20to%20discuss%20a%20project.');
}

function contactTelegram() {
    tg.HapticFeedback.notificationOccurred('success');
    tg.openTelegramLink('https://t.me/yourusername');
}

function bookCall() {
    tg.HapticFeedback.impactOccurred('heavy');
    tg.showPopup({
        title: '📅 Schedule Strategy Call',
        message: 'I\'ll redirect you to my calendar to book a 30-minute call. Choose a time that works for you!',
        buttons: [{
            type: 'default',
            text: 'Open Calendar',
            id: 'calendar'
        }]
    });
    
    tg.onEvent('popupButtonClicked', (data) => {
        if (data.button_id === 'calendar') {
            tg.openLink('https://calendly.com/yourusername/30min');
        }
    });
}

// Analytics Tracking
function initAnalytics() {
    // Track demo launches
    document.querySelectorAll('[onclick*="Demo"]').forEach(btn => {
        btn.addEventListener('click', function() {
            const demoType = this.textContent.toLowerCase();
            console.log(`Demo launched: ${demoType}`);
            // Here you can add actual analytics tracking
        });
    });
    
    // Track time spent
    let startTime = Date.now();
    window.addEventListener('beforeunload', () => {
        const timeSpent = Math.round((Date.now() - startTime) / 1000);
        console.log(`Time spent: ${timeSpent}s`);
    });
}

// Utility Functions
function scrollToSection(sectionId) {
    tg.HapticFeedback.impactOccurred('light');
    const section = document.getElementById(sectionId);
    if (section) {
        section.scrollIntoView({ behavior: 'smooth' });
    }
}

function showChatDemo(title, messages) {
    // Create modal for chat demo
    const modal = document.createElement('div');
    modal.className = 'chat-modal';
    modal.innerHTML = `
        <div class="chat-modal-content">
            <h3>${title}</h3>
            <div class="chat-history"></div>
            <div class="chat-input">
                <input type="text" placeholder="Type a message..." id="chatInput">
                <button onclick="sendMessage()">Send</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Add initial messages
    const history = modal.querySelector('.chat-history');
    messages.forEach(msg => {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-msg ${msg.role}`;
        messageDiv.textContent = msg.text;
        history.appendChild(messageDiv);
    });
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', initApp);