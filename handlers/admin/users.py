from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import Database
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
db = Database('shop.db')

async def manage_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user management menu with stats"""
    try:
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
            
            # Format date if it exists
            if created_at:
                try:
                    created_date = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y %H:%M')
                except:
                    created_date = str(created_at)
            else:
                created_date = "Bilinmiyor"
            
            message += f"{status} ID: {user_id}\n"
            message += f"📅 Kayıt: {created_date}\n"
            message += f"✅ Onaylanan: {completed or 0}\n"
            message += f"❌ Reddedilen: {rejected or 0}\n"
            message += f"⚠️ Başarısız: {failed or 0}\n"
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
            # If message is too long, send a simplified version
            simplified_message = "👥 Kullanıcı Listesi\n\nKullanıcıları yönetmek için aşağıdaki butonları kullanın:"
            await update.callback_query.message.edit_text(
                simplified_message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    except Exception as e:
        logger.error(f"Error in manage_users: {e}")
        await update.callback_query.message.edit_text(
            "❌ Kullanıcı listesi alınırken bir hata oluştu.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )

async def handle_user_ban_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle toggling user ban status"""
    try:
        query = update.callback_query
        user_id = int(query.data.split('_')[2])
        
        if db.toggle_user_ban(user_id):
            # Get updated user stats
            user_stats = db.get_user_stats(user_id)
            if user_stats:
                is_banned = user_stats[5]
                status = "yasaklandı" if is_banned else "yasağı kaldırıldı"
                
                # Notify the affected user
                try:
                    message = "⛔️ Hesabınız yasaklanmıştır." if is_banned else "✅ Hesabınızın yasağı kaldırılmıştır."
                    keyboard = [[InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]]
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=message,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                except Exception as e:
                    logger.error(f"Error notifying user {user_id}: {e}")
                
                # Show success message to admin
                await query.answer(f"Kullanıcı başarıyla {status}!")
            else:
                await query.answer("Kullanıcı bulunamadı!")
        else:
            await query.answer("İşlem başarısız oldu!")
        
        # Refresh users menu
        await manage_users(update, context)
    except Exception as e:
        logger.error(f"Error in handle_user_ban_toggle: {e}")
        await query.answer("İşlem sırasında bir hata oluştu!")