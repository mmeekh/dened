from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import Database
from config import ADMIN_ID
import logging

logger = logging.getLogger(__name__)
db = Database('shop.db')

async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start broadcast message process"""
    await update.callback_query.message.edit_text(
        "📢 Tüm kullanıcılara gönderilecek mesajı yazın:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 İptal", callback_data='main_menu')
        ]])
    )
    return BROADCAST_MESSAGE

async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send broadcast message to all users"""
    message = update.message.text
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        logger.warning(f"Non-admin user {user_id} tried to broadcast")
        return ConversationHandler.END
    
    try:
        await update.message.delete()
    except Exception as e:
        logger.error(f"Error deleting message: {e}")
    
    users = db.get_all_users()
    if not users:
        logger.warning("No users found in database")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Veritabanında kayıtlı kullanıcı bulunamadı.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )
        return ConversationHandler.END
    
    success_count = 0
    for user_id in users:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📢 Duyuru:\n\n{message}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
                ]])
            )
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to send broadcast to user {user_id}: {e}")
            continue
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"✅ Bildirim {success_count}/{len(users)} kullanıcıya gönderildi!",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
        ]])
    )
    
    return ConversationHandler.END