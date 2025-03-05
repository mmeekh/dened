from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import Database
from config import ADMIN_ID
from states import SUPPORT_TICKET
from utils.exchange import get_usdt_try_rate
import logging

logger = logging.getLogger(__name__)
db = Database('shop.db')

async def show_support_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show simplified support menu with admin contact"""
    try:
        # Delete previous message if exists
        if update.callback_query:
            try:
                await update.callback_query.message.delete()
            except Exception as e:
                logger.error(f"Error deleting message: {e}")
    except Exception as e:
        logger.error(f"Error in message cleanup: {e}")

    message = """ℹ️ Destek & Bilgi

Herhangi bir sorunuz veya sorununuz olduğunda doğrudan Admin ile iletişime geçebilirsiniz.

👨‍💻 Admin: @abstract53

❓ Sıkça sorulan soruları da inceleyebilirsiniz."""

    keyboard = [
        [InlineKeyboardButton("❓ Sıkça Sorulan Sorular", callback_data='faq')],
        [InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        reply_markup=reply_markup
    )

async def handle_support_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle support ticket creation"""
    user_id = update.effective_user.id
    message = update.message.text
    
    try:
        await update.message.delete()
    except Exception as e:
        logger.error(f"Error deleting user message: {e}")
    
    admin_message = f"📩 Yeni Destek Talebi\n\n"
    admin_message += f"👤 Kullanıcı ID: {user_id}\n"
    admin_message += f"💬 Mesaj:\n{message}"
    
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_message,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )
    except Exception as e:
        logger.error(f"Error forwarding support ticket to admin: {e}")
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="✅ Destek talebiniz başarıyla oluşturuldu. En kısa sürede size dönüş yapılacaktır.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
        ]])
    )
    
    return ConversationHandler.END

async def show_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show FAQ page with exchange rate information"""
    try:
        # Delete previous message if exists
        if update.callback_query:
            try:
                await update.callback_query.message.delete()
            except Exception as e:
                logger.error(f"Error deleting message: {e}")
    except Exception as e:
        logger.error(f"Error in message cleanup: {e}")

    # Get current exchange rate
    usdt_try_rate = get_usdt_try_rate()
    exchange_rate_text = f" (≈ {20 * usdt_try_rate:.2f} ₺ + transfer ücreti)" if usdt_try_rate else ""
    max_exchange_text = f" (≈ {1000 * usdt_try_rate:.2f} ₺ + transfer ücreti)" if usdt_try_rate else ""
    
    # Prepare exchange rate info for FAQ
    current_rate = f"\n\n💱 Güncel Kur: 1 USDT = {usdt_try_rate:.2f} ₺" if usdt_try_rate else ""

    message = f"""❓ S.S.S/Kurallar

📜 Genel Kurallar:
1. Adminlerle her zaman saygılı ve profesyonel iletişim kurulmalıdır
2. Spam veya kötüye kullanım yasaktır
3. Sahte ödeme bildirimi yapanlar anında yasaklanır{current_rate}

1️⃣ Ödeme yaptım, ne kadar beklemeliyim?
- Ödemeler ortalama 5-10 dakika içinde onaylanır

2️⃣ Hangi ödeme yöntemleri kabul ediliyor?
- Sadece USDT (TRC20) kabul edilmektedir

3️⃣ Minimum/Maksimum ödeme tutarı nedir?
- Minimum işlem tutarı: 20 USDT{exchange_rate_text}
- Maksimum işlem tutarı: 1000 USDT{max_exchange_text}

4️⃣ Ürün teslimi nasıl yapılıyor?
- Ödeme onaylandıktan sonra ürün konumu bot tarafından teslim edilir

5️⃣ Paramı geri alabilir miyim?
- Başarılı işlemlerde iade yapılmamaktadır

⚠️ Önemli Uyarı: Üç kez üst üste reddedilen sipariş hesabınızın kalıcı olarak yasaklanmasına neden olacaktır."""

    keyboard = [[InlineKeyboardButton("🔙 Destek Menüsüne Dön", callback_data='support_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        reply_markup=reply_markup
    )