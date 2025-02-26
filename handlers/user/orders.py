from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import Database
import logging

logger = logging.getLogger(__name__)
db = Database('shop.db')

async def show_orders_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the main orders menu with status counts"""
    user_id = update.effective_user.id
    
    pending_count = len(db.get_user_orders_by_status(user_id, 'pending'))
    completed_count = len(db.get_user_orders_by_status(user_id, 'completed'))
    rejected_count = len(db.get_user_orders_by_status(user_id, 'rejected'))
    
    keyboard = [
        [InlineKeyboardButton(f"⏳ Bekleyen ({pending_count})", callback_data='pending_orders')],
        [InlineKeyboardButton(f"✅ Tamamlanan ({completed_count})", callback_data='completed_orders')],
        [InlineKeyboardButton(f"❌ Reddedilen ({rejected_count})", callback_data='rejected_orders')],
        [InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    total_orders = pending_count + completed_count + rejected_count
    message = f"""🏷 Siparişlerim

📊 Sipariş Özeti:
• Toplam Sipariş: {total_orders}
• Bekleyen: {pending_count}
• Tamamlanan: {completed_count}
• Reddedilen: {rejected_count}

Detaylı bilgi için sipariş durumunu seçin:"""
    
    await update.callback_query.message.edit_text(
        text=message,
        reply_markup=reply_markup
    )

async def show_orders_by_status(update: Update, context: ContextTypes.DEFAULT_TYPE, status: str):
    """Show orders filtered by status"""
    user_id = update.effective_user.id
    orders = db.get_user_orders_by_status(user_id, status)
    
    status_emoji = {
        'pending': '⏳',
        'completed': '✅',
        'rejected': '❌'
    }
    
    status_text = {
        'pending': 'Beklemede',
        'completed': 'Tamamlandı',
        'rejected': 'Reddedildi'
    }
    
    if not orders:
        keyboard = [[InlineKeyboardButton("🔙 Siparişlere Dön", callback_data='orders_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.edit_text(
            f"{status_emoji[status]} {status_text[status]} siparişiniz bulunmamaktadır.",
            reply_markup=reply_markup
        )
        return

    message = f"{status_emoji[status]} {status_text[status]} Siparişleriniz:\n\n"
    keyboard = []
    
    for order in orders:
        message += f"🛍️ Sipariş #{order[0]}\n"
        message += f"📦 Ürünler:\n{order[5]}\n"
        message += f"💰 Toplam: {order[2]} USDT\n"
        message += f"📅 {order[4]}\n"
        message += f"📊 Durum: {status_text.get(order[3], order[3])}\n\n"
        
        keyboard.append([
            InlineKeyboardButton(
                f"🔍 Sipariş #{order[0]} Detayları",
                callback_data=f'view_order_{order[0]}'
            )
        ])

    keyboard.append([InlineKeyboardButton("🔙 Siparişlere Dön", callback_data='orders_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await update.callback_query.message.edit_text(
            message,
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error showing orders: {e}")
        simplified_message = f"{status_emoji[status]} {status_text[status]} Siparişleriniz\n\n"
        simplified_message += "Siparişlerinizi görüntülemek için aşağıdaki butonları kullanabilirsiniz."
        await update.callback_query.message.edit_text(
            simplified_message,
            reply_markup=reply_markup
        )

async def show_order_details(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: int):
    """Show detailed information about a specific order"""
    try:
        order = db.get_purchase_request(order_id)
        if not order:
            await update.callback_query.message.edit_text(
                "❌ Sipariş bulunamadı!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Siparişlere Dön", callback_data='orders_menu')
                ]])
            )
            return

        message = f"🛍️ Sipariş #{order['id']}\n\n"
        message += f"📦 Ürünler:\n{order['items']}\n"
        message += f"💰 Toplam: {order['total_amount']} USDT\n"
        message += f"📅 Tarih: {order['created_at']}\n"
        message += f"📊 Durum: {order['status']}\n"

        if order['status'] == 'completed':
            message += "\n✅ Siparişiniz tamamlandı!"
        elif order['status'] == 'pending':
            message += "\n⏳ Siparişiniz onay bekliyor..."
        elif order['status'] == 'rejected':
            message += "\n❌ Siparişiniz reddedildi."

        keyboard = [
            [InlineKeyboardButton("🔙 Siparişlere Dön", callback_data='orders_menu')]
        ]
        
        await update.callback_query.message.edit_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logger.error(f"Error showing order details: {e}")
        await update.callback_query.message.edit_text(
            "❌ Sipariş detayları gösterilirken bir hata oluştu.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Siparişlere Dön", callback_data='orders_menu')
            ]])
        )