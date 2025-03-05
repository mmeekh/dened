from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import Database
from config import ADMIN_ID
import logging
from states import BROADCAST_MESSAGE

logger = logging.getLogger(__name__)
db = Database('shop.db')

async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start broadcast message process"""
    logger.info(f"Starting broadcast process for user {update.effective_user.id}")
    try:
        # Önceki içeriği koruyoruz, ama show_generic_menu'yu kullanıyoruz
        from utils.menu_utils import show_generic_menu
        
        await show_generic_menu(
            update=update,
            context=context,
            text="📢 Tüm kullanıcılara gönderilecek mesajı yazın:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 İptal", callback_data='main_menu')
            ]])
        )
        
        logger.info("Broadcast message prompt displayed")
        return BROADCAST_MESSAGE
    except Exception as e:
        logger.error(f"Error starting broadcast: {e}")
        try:
            await show_generic_menu(
                update=update,
                context=context,
                text="❌ Bildirim başlatılırken bir hata oluştu.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
                ]])
            )
        except Exception as inner_e:
            logger.error(f"Error sending error message: {inner_e}")
        return ConversationHandler.END

async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send broadcast message to all users"""
    message = update.message.text
    user_id = update.effective_user.id
    
    logger.info(f"Processing broadcast for user {user_id} with message: {message[:20]}...")
    
    if user_id != ADMIN_ID:
        logger.warning(f"Non-admin user {user_id} tried to broadcast")
        return ConversationHandler.END
    
    try:
        await update.message.delete()
    except Exception as e:
        logger.error(f"Error deleting message: {e}")
    
    try:
        # Get all non-banned users directly using SQL
        logger.info("Fetching users from database using direct query")
        try:
            # Execute a direct SQL query to get users
            db.cur.execute("SELECT DISTINCT telegram_id FROM users WHERE is_banned = 0")
            users = [int(row[0]) for row in db.cur.fetchall()]
            logger.info(f"Retrieved {len(users)} users from database")
        except Exception as e:
            logger.error(f"Error in SQL query to get users: {e}")
            users = []
        
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
        
        logger.info(f"Starting to send broadcasts to {len(users)} users")
        success_count = 0
        failed_count = 0
        failed_users = []
        
        # Process users in smaller batches to avoid overloading
        batch_size = 20
        for i in range(0, len(users), batch_size):
            batch = users[i:i+batch_size]
            for user_id in batch:
                try:
                    logger.debug(f"Sending message to user {user_id}")
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"📢 Duyuru:\n\n{message}",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
                        ]])
                    )
                    success_count += 1
                    logger.debug(f"Successfully sent broadcast to user {user_id}")
                except Exception as e:
                    failed_count += 1
                    failed_users.append(user_id)
                    logger.error(f"Failed to send broadcast to user {user_id}: {e}")
                    continue
        
        logger.info(f"Broadcast completed. Successful: {success_count}, Failed: {failed_count}")
        if failed_count > 0:
            logger.info(f"Failed users: {failed_users}")
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"✅ Bildirim {success_count}/{len(users)} kullanıcıya gönderildi!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )
        
    except Exception as e:
        logger.error(f"Error in broadcast process: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Bildirim gönderilirken bir hata oluştu.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )
    
    logger.info("Broadcast process completed")
    return ConversationHandler.END