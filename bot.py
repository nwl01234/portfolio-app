import asyncio
import logging
import json
import sys
from datetime import datetime
from aiogram import Bot, Dispatcher, F, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, WebAppInfo, ReplyKeyboardMarkup,
    KeyboardButton, InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import BOT_TOKEN, APP_URL, ADMIN_ID, USDT_WALLET, BTC_WALLET

# Настройка логирования
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# Инициализация
dp = Dispatcher()

# Хранение данных
orders_db = {}
conversations_db = {}

# ========== КЛАВИАТУРЫ ==========
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚀 Open Portfolio App", web_app=WebAppInfo(url=APP_URL))],
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
@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    user_name = html.quote(message.from_user.full_name)
    
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🚀 Open Portfolio App", 
        web_app=WebAppInfo(url=APP_URL)
    )
    
    text = (
        f"Hi, {user_name}! 👋\n\n"
        f"I am a **Full-Stack Bot Developer** ready to automate your business.\n\n"
        f"👇 **Click the button below** to launch my interactive portfolio inside Telegram.\n"
        f"You will see live demos of e-commerce, analytics, and automation tools."
    )
    
    await message.answer(
        text,
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Отправляем основную клавиатуру с меню
    await message.answer(
        "Use the buttons below for quick access:",
        reply_markup=get_main_keyboard()
    )
    
    # Показываем админ-панель если это админ
    if str(message.from_user.id) == ADMIN_ID:
        await message.answer(
            "👨‍💻 *Admin Panel*",
            reply_markup=get_admin_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

# ========== ОБРАБОТКА ЗАКАЗОВ ИЗ WEB APP ==========
@dp.message(F.content_type == "web_app_data")
async def handle_web_app_data(message: Message):
    try:
        data = json.loads(message.web_app_data.data)
        logging.info(f"Received web app data: {data}")
        
        if data.get('type') == 'order':
            # Создаем заказ
            order_id = f"ORD-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            orders_db[order_id] = {
                **data,
                'order_id': order_id,
                'customer_id': message.from_user.id,
                'customer_username': message.from_user.username,
                'status': 'pending_payment',
                'created_at': datetime.now().isoformat()
            }
            
            # Форматируем список товаров
            items_list = "\n".join([f"   • {item}" for item in data['items'].split(', ')])
            
            # Сообщение клиенту
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
            
            # Автоматически отправляем реквизиты
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
                
                # Кнопки быстрого ответа
                quick_kb = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="💬 Reply to Client", 
                                callback_data=f"reply_{message.from_user.id}"
                            ),
                            InlineKeyboardButton(
                                text="✅ Mark as Paid", 
                                callback_data=f"paid_{order_id}"
                            )
                        ]
                    ]
                )
                
                await message.bot.send_message(
                    ADMIN_ID,
                    admin_text,
                    reply_markup=quick_kb,
                    parse_mode=ParseMode.MARKDOWN
                )
        
        elif data.get('type') == 'support_message':
            # Обработка сообщений поддержки
            support_text = f"""
📩 *New Support Message*

👤 *From:* @{data.get('user', {}).get('username', 'Unknown')}
🆔 *User ID:* `{data.get('user', {}).get('id', 'Unknown')}`
💬 *Message:*
{data.get('text', 'No text')}

⏰ *Time:* {datetime.now().strftime('%H:%M %d.%m.%Y')}
            """
            
            # Сохраняем в историю
            conv_key = str(data.get('user', {}).get('id'))
            if conv_key not in conversations_db:
                conversations_db[conv_key] = []
            
            conversations_db[conv_key].append({
                'role': 'user',
                'text': data.get('text', ''),
                'time': datetime.now().isoformat()
            })
            
            # Отправляем админу
            if ADMIN_ID:
                await message.bot.send_message(
                    ADMIN_ID,
                    support_text,
                    parse_mode=ParseMode.MARKDOWN
                )
    
    except Exception as e:
        logging.error(f"Error processing web app data: {e}")
        await message.answer("❌ Error processing your request. Please try again.")

# ========== ОТПРАВКА РЕКВИЗИТОВ ==========
async def send_payment_details(user_id: int, order_id: str):
    """Отправляет пользователю реквизиты для оплаты"""
    try:
        if order_id not in orders_db:
            await dp.bot.send_message(user_id, "❌ Order not found.")
            return
        
        order = orders_db[order_id]
        total_usd = float(order['total'])
        
        # Расчёт суммы в BTC (примерный курс)
        btc_amount = total_usd / 45000
        
        # Формируем сообщение с реквизитами (БЕЗ проблем с f-строками!)
        payment_text = f"💳 *Payment Details for Order {order_id}*\n\n"
        payment_text += f"💰 *Amount:* ${order['total']}\n"
        payment_text += f"📦 *Items:* {order['items']}\n\n"
        payment_text += "*Choose payment method:*\n\n"
        
        # USDT блок
        payment_text += "1️⃣ *Crypto (USDT - TRC20):*\n"
        payment_text += "   ```\n"
        payment_text += f"   Address: {USDT_WALLET}\n"
        payment_text += f"   Amount: {order['total']} USDT\n"
        payment_text += "   Network: TRON (TRC20)\n"
        payment_text += f"   Memo/Message: {order_id}\n"
        payment_text += "   ```\n\n"
        
        # BTC блок
        payment_text += "2️⃣ *Crypto (BTC):*\n"
        payment_text += "   ```\n"
        payment_text += f"   Address: {BTC_WALLET}\n"
        payment_text += f"   Amount: {btc_amount:.6f} BTC\n"
        payment_text += f"   Memo/Message: {order_id}\n"
        payment_text += "   ```\n\n"
        
        payment_text += "⚠️ *Important:*\n"
        payment_text += f"• Send exact amount\n"
        payment_text += f"• Include order ID `{order_id}` in transaction memo/message\n"
        payment_text += f"• After payment, send screenshot to this chat\n"
        payment_text += f"• Order starts in 24h after payment confirmation\n\n"
        payment_text += "Need help? Use *Support Chat*."
        
        await dp.bot.send_message(
            user_id,
            payment_text,
            parse_mode=ParseMode.MARKDOWN
        )
        
        logging.info(f"Payment details sent for order {order_id} to user {user_id}")
        
    except Exception as e:
        logging.error(f"Error sending payment details: {e}")
        await dp.bot.send_message(user_id, "❌ Error generating payment details.")

# ========== АДМИН КОМАНДЫ ==========
@dp.message(Command("pay"))
async def pay_command(message: Message):
    """Административная команда для отправки реквизитов"""
    if str(message.from_user.id) != ADMIN_ID:
        return
    
    try:
        args = message.text.split()
        if len(args) < 2:
            await message.answer("Usage: /pay ORDER_ID")
            return
        
        order_id = args[1]
        if order_id not in orders_db:
            await message.answer(f"❌ Order {order_id} not found.")
            return
        
        order = orders_db[order_id]
        customer_id = order['customer_id']
        
        await send_payment_details(customer_id, order_id)
        await message.answer(f"✅ Payment details sent for order {order_id}")
        
    except Exception as e:
        logging.error(f"Error in pay command: {e}")
        await message.answer(f"❌ Error: {str(e)}")

@dp.message(Command("orders"))
async def list_orders(message: Message):
    if str(message.from_user.id) != ADMIN_ID:
        await message.answer("❌ Admin only command.")
        return
    
    if not orders_db:
        await message.answer("📭 No orders yet.")
        return
    
    orders_list = []
    for order_id, order in orders_db.items():
        status_emoji = "🟡" if order['status'] == 'pending_payment' else "🟢" if order['status'] == 'paid' else "🔴"
        orders_list.append(
            f"{status_emoji} *{order_id}* - ${order['total']} - {order['status']}\n"
            f"   Client: @{order.get('customer_username', 'N/A')}\n"
            f"   Items: {order['items'][:50]}...\n"
        )
    
    await message.answer(
        f"📦 *All Orders ({len(orders_db)})*\n\n" + "\n".join(orders_list),
        parse_mode=ParseMode.MARKDOWN
    )

@dp.message(Command("reply"))
async def reply_command(message: Message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    
    try:
        args = message.text.split(maxsplit=2)
        if len(args) < 3:
            await message.answer("Usage: /reply USER_ID Your message here")
            return
        
        user_id = int(args[1])
        reply_text = args[2]
        
        await message.bot.send_message(
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
        logging.error(f"Error in reply command: {e}")
        await message.answer(f"❌ Error: {str(e)}")

# ========== CALLBACK QUERIES ==========
@dp.callback_query()
async def handle_callbacks(callback):
    data = callback.data
    
    if data.startswith("reply_"):
        user_id = data.replace("reply_", "")
        await callback.message.answer(
            f"Use /reply {user_id} to send a message to this user."
        )
    
    elif data.startswith("paid_"):
        order_id = data.replace("paid_", "")
        if order_id in orders_db:
            orders_db[order_id]['status'] = 'paid'
            await callback.message.answer(f"✅ Order {order_id} marked as paid.")
            
            # Уведомляем клиента
            customer_id = orders_db[order_id]['customer_id']
            await dp.bot.send_message(
                customer_id,
                f"✅ *Payment Confirmed!*\n\n"
                f"Your payment for order `{order_id}` has been confirmed.\n"
                f"Development will start within 24 hours.\n\n"
                f"Thank you for your order!",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await callback.message.answer(f"❌ Order {order_id} not found.")
    
    elif data == "view_orders":
        # Создаем фиктивное сообщение для вызова команды
        from aiogram.types import Message as MsgType
        fake_msg = MsgType(
            message_id=callback.message.message_id,
            date=callback.message.date,
            chat=callback.message.chat,
            from_user=callback.message.from_user
        )
        await list_orders(fake_msg)
    
    await callback.answer()

# ========== СИСТЕМА ЧАТА ==========
@dp.message(F.text == "💬 Support Chat")
async def support_chat(message: Message):
    await message.answer(
        """💬 *Support Chat*

You can now send any message, and it will be forwarded to the developer.

I typically respond within *1-2 hours* during business hours (EST).

*What to include:*
• Your project description
• Budget range
• Deadline
• Any specific requirements

Or just say hello! 👋""",
        parse_mode=ParseMode.MARKDOWN
    )

# Пересылка сообщений от клиентов админу
@dp.message(F.chat.id != int(ADMIN_ID))
async def forward_to_admin(message: Message):
    if not message.web_app_data:  # Исключаем данные из веб-приложения
        if ADMIN_ID:
            # Сохраняем в историю
            user_id = str(message.from_user.id)
            if user_id not in conversations_db:
                conversations_db[user_id] = []
            
            conversations_db[user_id].append({
                'role': 'user',
                'text': message.text or "Media message",
                'time': datetime.now().isoformat()
            })
            
            if message.text:
                forward_text = f"""
📨 *New Message from Client*

👤 *From:* @{message.from_user.username or 'No username'}
🆔 *User ID:* `{message.from_user.id}`
💬 *Message:*
{message.text}

⏰ *Time:* {datetime.now().strftime('%H:%M %d.%m.%Y')}
                """
                
                reply_kb = InlineKeyboardMarkup(
                    inline_keyboard=[[
                        InlineKeyboardButton(
                            text="💬 Reply",
                            callback_data=f"reply_{message.from_user.id}"
                        )
                    ]]
                )
                
                await message.bot.send_message(
                    ADMIN_ID,
                    forward_text,
                    reply_markup=reply_kb,
                    parse_mode=ParseMode.MARKDOWN
                )

# Ответ админа через реплай
@dp.message(F.reply_to_message & (F.from_user.id == int(ADMIN_ID)))
async def admin_reply(message: Message):
    try:
        reply_text = message.reply_to_message.text or ""
        import re
        user_id_match = re.search(r'User ID.*?(\d+)', reply_text)
        
        if user_id_match:
            user_id = int(user_id_match.group(1))
            
            await message.bot.send_message(
                user_id,
                f"👨‍💻 *Developer Reply:*\n\n{message.text}",
                parse_mode=ParseMode.MARKDOWN
            )
            
            if str(user_id) not in conversations_db:
                conversations_db[str(user_id)] = []
            
            conversations_db[str(user_id)].append({
                'role': 'admin',
                'text': message.text,
                'time': datetime.now().isoformat()
            })
            
            await message.answer("✅ Message sent to client.")
        else:
            await message.answer("❌ Could not find user ID. Use /reply command instead.")
    
    except Exception as e:
        logging.error(f"Error in admin reply: {e}")
        await message.answer(f"❌ Error: {str(e)}")

# ========== ДРУГИЕ КОМАНДЫ ==========
@dp.message(F.text == "📦 My Orders")
async def my_orders(message: Message):
    user_orders = []
    for order_id, order in orders_db.items():
        if order.get('customer_id') == message.from_user.id:
            status_emoji = "🟡" if order['status'] == 'pending_payment' else "🟢" if order['status'] == 'paid' else "🔴"
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
async def pricing_info(message: Message):
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
async def about_dev(message: Message):
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
async def main() -> None:
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")