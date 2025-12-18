import os
import json
import logging
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    WebAppInfo,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    LabeledPrice
)
from aiogram.enums import ParseMode
from dotenv import load_dotenv

# ========== ЗАГРУЗКА НАСТРОЕК ==========
load_dotenv()  # <-- Важно: загружаем переменные из .env

TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-username.github.io/portfolio-app/")

# Загружаем ваши крипто-кошельки из .env
USDT_WALLET = os.getenv("USDT_WALLET", "Ваш_USDT_адрес_не_найден")
BTC_WALLET = os.getenv("BTC_WALLET", "Ваш_BTC_адрес_не_найден")

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Хранение данных (в реальном проекте используйте базу данных)
orders_db = {}
conversations_db = {}

# ========== КЛАВИАТУРЫ ==========
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚀 Open Portfolio App", web_app=WebAppInfo(url=WEBAPP_URL))],
            [KeyboardButton(text="💬 Support Chat"), KeyboardButton(text="📦 My Orders")],
            [KeyboardButton(text="👨‍💻 About Developer"), KeyboardButton(text="💰 Pricing")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Select an option..."
    )

def get_admin_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 View Orders", callback_data="view_orders")],
            [InlineKeyboardButton(text="📢 Broadcast", callback_data="broadcast")],
            [InlineKeyboardButton(text="🔄 Update App", callback_data="update_app")]
        ]
    )

# ========== КОМАНДА /START ==========
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    welcome_text = """
👋 *Welcome to NextGen Automation*

I develop *high-performance Telegram bots* for US businesses, creators, and startups.

✨ *Core Services:*
• 🤖 AI-Powered Sales Agents
• 📊 Real-time Data Monitoring
• 💬 Community Management Bots
• ⚡️ Full Automation Solutions

💰 *Transparent Pricing:* $149 – $1,200
⏱ *Delivery Time:* 3–14 days

Tap *'Open Portfolio App'* to see interactive demos and place orders!
    """
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    
    if str(message.from_user.id) == ADMIN_ID:
        await message.answer("👨‍💻 *Admin Panel*", reply_markup=get_admin_keyboard(), parse_mode=ParseMode.MARKDOWN)

# ========== ОБРАБОТКА ЗАКАЗОВ ИЗ WEB APP ==========
@dp.message(F.content_type == "web_app_data")
async def handle_web_app_data(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        logger.info(f"Received web app data: {data}")
        
        if data.get('type') == 'order':
            order_id = f"ORD-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            orders_db[order_id] = {
                **data,
                'order_id': order_id,
                'customer_id': message.from_user.id,
                'customer_username': message.from_user.username,
                'status': 'pending_payment',
                'created_at': datetime.now().isoformat()
            }
            
            items_list = "\n".join([f"   • {item}" for item in data['items'].split(', ')])
            
            # Сообщение клиенту о принятом заказе
            await message.answer(
                f"""✅ *Order Received!*

📦 *Order ID:* `{order_id}`
🛒 *Items:*
{items_list}
💰 *Total:* ${data['total']}
💳 *Selected Method:* {data['payment'].upper()}

📝 *Next Steps:*
I will send you payment details shortly.""",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # АВТОМАТИЧЕСКИ отправляем реквизиты для оплаты
            # Используем команду /pay, передавая order_id
            await send_payment_details(message.from_user.id, order_id)
            
            # Уведомление админу
            if ADMIN_ID:
                admin_text = f"""
🚨 *NEW ORDER!*

📋 *Order ID:* `{order_id}`
👤 *Client:* @{message.from_user.username} (ID: `{message.from_user.id}`)
📦 *Items:* {data['items']}
💰 *Amount:* ${data['total']}
💳 *Method:* {data['payment']}
⏰ *Time:* {datetime.now().strftime('%H:%M %d.%m.%Y')}

Payment details sent automatically.
                """
                
                quick_kb = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(text="💬 Reply to Client", 
                                               callback_data=f"reply_{message.from_user.id}"),
                            InlineKeyboardButton(text="✅ Mark as Paid", 
                                               callback_data=f"paid_{order_id}")
                        ]
                    ]
                )
                
                await bot.send_message(
                    ADMIN_ID,
                    admin_text,
                    reply_markup=quick_kb,
                    parse_mode=ParseMode.MARKDOWN
                )
                
        elif data.get('type') == 'support_message':
            # ... (код обработки сообщений поддержки без изменений)
            pass
            
    except Exception as e:
        logger.error(f"Error processing web app data: {e}")
        await message.answer("❌ Error processing your request. Please try again.")

# ========== КОМАНДА /PAY ДЛЯ ОТПРАВКИ РЕКВИЗИТОВ ==========
async def send_payment_details(user_id: int, order_id: str):
    """Отправляет пользователю реквизиты для оплаты"""
    try:
        if order_id not in orders_db:
            await bot.send_message(user_id, "❌ Order not found.")
            return
        
        order = orders_db[order_id]
        total_usd = float(order['total'])
        
        # Расчёт суммы в BTC (примерный курс)
        btc_amount = total_usd / 45000  # Используйте актуальный курс
        
        # Формируем сообщение с реквизитами
        # ИСПРАВЛЕНИЕ: Всё внутри одной f-строки с тройными кавычками
        payment_text = f"""
💳 *Payment Details for Order {order_id}*

💰 *Amount:* ${order['total']}
📦 *Items:* {order['items']}

*Choose payment method:*

1️⃣ *Crypto (USDT - TRC20):*
Address: {USDT_WALLET}
Amount: {order['total']} USDT
Network: TRON (TRC20)
Memo/Message: {order_id}
2️⃣ *Crypto (BTC):*
Address: {BTC_WALLET}
Amount: {btc_amount:.6f} BTC
Memo/Message: {order_id}

3️⃣ *Telegram Wallet:*
Send payment to @your_wallet_bot with note "{order_id}"

⚠️ *Important:*
• Send exact amount
• Include order ID in memo
• Screenshot payment confirmation
• Reply with confirmation screenshot

After payment, your order will start in 24h.
     """
     
     await bot.send_message(
         customer_id,
         payment_text,
         parse_mode=ParseMode.MARKDOWN
     )
     
     await message.answer(f"✅ Payment details sent for order {order_id}")
     
     # Обновляем статус
     orders_db[order_id]['status'] = 'payment_sent'
     
 except Exception as e:
     logger.error(f"Error sending payment: {e}")
     await message.answer(f"❌ Error: {str(e)}")

@dp.message(Command("reply"))
async def reply_command(message: types.Message):
 if str(message.from_user.id) != ADMIN_ID:
     return
 
 try:
     args = message.text.split(maxsplit=2)
     if len(args) < 3:
         await message.answer("Usage: /reply USER_ID Your message here")
         return
     
     user_id = int(args[1])
     reply_text = args[2]
     
     await bot.send_message(
         user_id,
         f"👨‍💻 *Developer Reply:*\n\n{reply_text}",
         parse_mode=ParseMode.MARKDOWN
     )
     
     # Сохраняем в историю
     if str(user_id) not in conversations_db:
         conversations_db[str(user_id)] = []
     
     conversations_db[str(user_id)].append({
         'role': 'admin',
         'text': reply_text,
         'time': datetime.now().isoformat()
     })
     
     await message.answer("✅ Message sent.")
 
 except Exception as e:
     logger.error(f"Error in reply command: {e}")
     await message.answer(f"❌ Error: {str(e)}")

# ========== CALLBACK QUERIES ==========
@dp.callback_query()
async def handle_callbacks(callback: types.CallbackQuery):
 data = callback.data
 
 if data.startswith("reply_"):
     user_id = data.replace("reply_", "")
     await callback.message.answer(
         f"Use /reply {user_id} to send a message to this user."
     )
 
 elif data.startswith("payment_"):
     order_id = data.replace("payment_", "")
     await callback.message.answer(
         f"Use /pay {order_id} to send payment details for this order."
     )
 
 elif data.startswith("paid_"):
     order_id = data.replace("paid_", "")
     if order_id in orders_db:
         orders_db[order_id]['status'] = 'paid'
         await callback.message.answer(f"✅ Order {order_id} marked as paid.")
     else:
         await callback.message.answer(f"❌ Order {order_id} not found.")
 
 elif data == "view_orders":
     await list_orders(callback.message)
 
 await callback.answer()

# ========== ДРУГИЕ КОМАНДЫ ==========
@dp.message(F.text == "📦 My Orders")
async def my_orders(message: types.Message):
 user_orders = []
 for order_id, order in orders_db.items():
     if order.get('customer_id') == message.from_user.id:
         status_emoji = "🟡" if order['status'] == 'pending' else "🟢" if order['status'] == 'paid' else "🔴"
         user_orders.append(
             f"{status_emoji} *{order_id}*\n"
             f"   Amount: ${order['total']}\n"
             f"   Status: {order['status']}\n"
             f"   Date: {order['created_at'][:10]}\n"
         )
 
 if user_orders:
     await message.answer(
         f"📦 *Your Orders*\n\n" + "\n".join(user_orders),
         parse_mode=ParseMode.MARKDOWN
     )
 else:
     await message.answer("📭 You have no orders yet. Open the Portfolio App to place one!")

@dp.message(F.text == "💰 Pricing")
async def pricing_info(message: types.Message):
 pricing_text = """
💰 *Transparent Pricing*

*Standard Services:*
• Basic AI Assistant – $299
• Simple Data Scraper – $199  
• Community Lite – $149

*Premium Services:*
• AI Sales Agent – $1,200
• Data Miner Pro – $900
• Crypto Community – $800

*What's included:*
✅ 30-day support
✅ Full documentation
✅ Source code ownership
✅ 1 round of revisions

*Payment Options:*
• Crypto (USDT/BTC) – 2% discount
• Telegram Wallet
• Bank transfer (US only)

All prices in USD. 50% deposit to start.
 """
 
 await message.answer(pricing_text, parse_mode=ParseMode.MARKDOWN)

@dp.message(F.text == "👨‍💻 About Developer")
async def about_dev(message: types.Message):
 about_text = """
👨‍💻 *About the Developer*

I specialize in creating *high-performance Telegram automation* for US businesses and startups.

*Experience:*
• 3+ years in bot development
• 50+ successful projects
• Clients in USA, Canada, EU

*Tech Stack:*
• Python (aiogram, Django)
• JavaScript (Telegram Mini Apps)
• PostgreSQL / Redis
• AWS / Docker

*Why work with me:*
1. **Fast delivery** – 3-14 days
2. **Clear communication** – daily updates
3. **Post-launch support** – 30 days included
4. **Transparent pricing** – no hidden fees

Let's build something amazing! 🚀
 """
 
 await message.answer(about_text, parse_mode=ParseMode.MARKDOWN)

# ========== ЗАПУСК ==========
async def main():
 logger.info("🚀 Bot starting...")
 await dp.start_polling(bot)

if __name__ == "__main__":
 asyncio.run(main())