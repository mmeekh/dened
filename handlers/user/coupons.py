from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import Database
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
db = Database('shop.db')

async def show_my_coupons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's available coupons in an organized way"""
    try:
        user_id = update.effective_user.id
        
        # Get all coupons for the user
        db.cur.execute(
            """SELECT coupon_code, discount_percent, source, expires_at, is_used, created_at
               FROM discount_coupons 
               WHERE user_id = ?
               ORDER BY is_used ASC, created_at DESC""",
            (user_id,)
        )
        all_coupons = db.cur.fetchall()
        
        # Organize coupons into active and used
        active_coupons = []
        used_coupons = []
        
        for coupon in all_coupons:
            code, discount, source, expires_at, is_used, created_at = coupon
            
            # Check if expired
            is_expired = False
            expires_text = ""
            if expires_at:
                try:
                    expiry_date = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')
                    is_expired = expiry_date < datetime.now()
                    expires_text = f"\n⏰ Son Kullanım: {expiry_date.strftime('%d.%m.%Y')}"
                except Exception as e:
                    logger.error(f"Date parsing error: {e}")
            
            # Format coupon details
            coupon_info = {
                "code": code,
                "discount": discount,
                "source": source,
                "expires_text": expires_text,
                "is_expired": is_expired,
                "is_used": is_used,
                "created_at": created_at
            }
            
            if is_used:
                used_coupons.append(coupon_info)
            elif not is_expired:
                active_coupons.append(coupon_info)
        
        # Create message with properly formatted coupon information
        message = "🎟️ Kuponlarım\n\n"
        
        if not all_coupons:
            message += "Henüz hiç kuponunuz bulunmuyor.\n\n"
            message += "💡 İpucu: Oyun oynayarak veya özel etkinliklere katılarak kupon kazanabilirsiniz!"
        else:
            # Active coupons section
            if active_coupons:
                message += "✅ AKTİF KUPONLAR:\n\n"
                for i, coupon in enumerate(active_coupons):
                    message += f"🎟️ {coupon['code']}\n"
                    message += f"💯 İndirim: %{coupon['discount']}\n"
                    message += f"📋 Kaynak: {coupon['source']}{coupon['expires_text']}\n"
                    if i < len(active_coupons) - 1:
                        message += "\n"  # Add extra line between coupons
            else:
                message += "❌ Aktif kuponunuz bulunmuyor.\n\n"
            
            # Used/expired coupons section
            if used_coupons:
                if active_coupons:
                    message += "\n"  # Separate sections
                    
                message += "🕒 KULLANILMIŞ KUPONLAR:\n\n"
                for i, coupon in enumerate(used_coupons[:5]):  # Show only the last 5 used coupons
                    message += f"🎟️ {coupon['code']}\n"
                    message += f"💯 İndirim: %{coupon['discount']}\n"
                    message += f"📋 Kaynak: {coupon['source']}\n"
                    if i < min(len(used_coupons), 5) - 1:
                        message += "\n"  # Add extra line between coupons
                
                # If there are more used coupons than shown
                if len(used_coupons) > 5:
                    message += f"\n... ve {len(used_coupons) - 5} daha"
        
        # Add buttons
        keyboard = []
        
        if active_coupons:
            keyboard.append([InlineKeyboardButton("🛒 Alışverişe Başla", callback_data='products_menu')])
        
        keyboard.append([InlineKeyboardButton("🎮 Oyun Oyna & Kupon Kazan", callback_data='games_menu')])
        keyboard.append([InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')])
        
        # Show the message
        await update.callback_query.message.edit_text(
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing coupons: {e}")
        await update.callback_query.message.edit_text(
            "❌ Kuponlarınız gösterilirken bir hata oluştu.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )