from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import Database
from config import ADMIN_ID
from states import SUPPORT_TICKET
import logging

logger = logging.getLogger(__name__)
db = Database('shop.db')

async def show_support_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show support menu"""
    try:
        await update.callback_query.message.delete()
    except Exception as e:
        logger.error(f"Error deleting message: {e}")

    keyboard = [
        [InlineKeyboardButton("📞 Destek Talebi Oluştur", callback_data='create_ticket')],
        [InlineKeyboardButton("❓ Sıkça Sorulan Sorular", callback_data='faq')],
        [InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="ℹ️ Destek & Bilgi",
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
    """Show FAQ page"""
    try:
        await update.callback_query.message.delete()
    except Exception as e:
        logger.error(f"Error deleting message: {e}")

    message = """❓ S.S.S/Kurallar

📜 Genel Kurallar:
1. Adminlerle her zaman saygılı ve profesyonel iletişim kurulmalıdır
2. Spam veya kötüye kullanım yasaktır
3. Sahte ödeme bildirimi yapanlar anında yasaklanır

1️⃣ Ödeme yaptım, ne kadar beklemeliyim?
- Ödemeler ortalama 5-10 dakika içinde onaylanır

2️⃣ Hangi ödeme yöntemleri kabul ediliyor?
- Sadece USDT (TRC20) kabul edilmektedir

3️⃣ Minimum/Maksimum ödeme tutarı nedir?
- Minimum işlem tutarı: 20 USDT
- Maksimum işlem tutarı: 1000 USDT

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