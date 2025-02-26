from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import Database
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
db = Database('shop.db')

async def manage_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user management menu"""
    users = db.get_all_users_with_stats()
    
    if not users:
        await update.callback_query.message.edit_text(
            "Henüz kayıtlı kullanıcı bulunmamaktadır.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )
        return

    message = "👥 Kullanıcı Listesi:\n\n"
    keyboard = []
    
    for user in users:
        user_id, created_at, completed, rejected, failed, is_banned = user
        status = "🚫" if is_banned else "✅"
        created_date = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y %H:%M')
        
        message += f"{status} ID: {user_id}\n"
        message += f"📅 Kayıt: {created_date}\n"
        message += f"✅ Onaylanan: {completed}\n"
        message += f"❌ Reddedilen: {rejected}\n"
        message += f"⚠️ Başarısız: {failed}\n"
        message += "───────────────\n"
        
        action = "Yasağı Kaldır" if is_banned else "Yasakla"
        keyboard.append([
            InlineKeyboardButton(
                f"{'🔓' if is_banned else '🔒'} {action} (ID: {user_id})",
                callback_data=f'toggle_ban_{user_id}'
            )
        ])

    keyboard.append([InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')])
    
    try:
        await update.callback_query.message.edit_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error showing users menu: {e}")
        simplified_message = "👥 Kullanıcı Listesi\n\nKullanıcıları yönetmek için aşağıdaki butonları kullanın:"
        await update.callback_query.message.edit_text(
            simplified_message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )