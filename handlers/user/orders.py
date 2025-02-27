from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import Database
import logging

logger = logging.getLogger(__name__)
db = Database('shop.db')

# Define status emojis and texts
STATUS_EMOJI = {
    'pending': '⏳',
    'completed': '✅',
    'rejected': '❌'
}

STATUS_TEXT = {
    'pending': 'Beklemede',
    'completed': 'Tamamlandı',
    'rejected': 'Reddedildi'
}

async def show_orders_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the main orders menu with status counts"""
    user_id = update.effective_user.id
    
    try:
        # Get counts directly with SQL queries
        pending_count = get_order_count_by_status(user_id, 'pending')
        completed_count = get_order_count_by_status(user_id, 'completed')
        rejected_count = get_order_count_by_status(user_id, 'rejected')
        
        keyboard = [
            [InlineKeyboardButton(f"⏳ Bekleyen Siparişler ({pending_count})", callback_data='pending_orders')],
            [InlineKeyboardButton(f"✅ Tamamlanan Siparişler ({completed_count})", callback_data='completed_orders')],
            [InlineKeyboardButton(f"❌ Reddedilen Siparişler ({rejected_count})", callback_data='rejected_orders')],
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
    except Exception as e:
        logger.error(f"Error showing orders menu: {e}")
        await update.callback_query.message.edit_text(
            "Bir hata oluştu. Lütfen tekrar deneyin.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )

def get_order_count_by_status(user_id, status):
    """Get count of orders by status using direct SQL query"""
    try:
        db.cur.execute(
            "SELECT COUNT(*) FROM purchase_requests WHERE user_id = ? AND status = ?",
            (user_id, status)
        )
        result = db.cur.fetchone()
        return result[0] if result else 0
    except Exception as e:
        logger.error(f"Error getting order count: {e}")
        return 0

def get_orders_by_status(user_id, status):
    """Get orders by status using direct SQL query"""
    try:
        query = """
            SELECT 
                pr.id,
                pr.user_id,
                pr.total_amount,
                pr.status,
                pr.created_at,
                GROUP_CONCAT(
                    p.name || ' (x' || pri.quantity || ' @ ' || pri.price || ' USDT)'
                ) as items
            FROM purchase_requests pr
            JOIN purchase_request_items pri ON pr.id = pri.request_id
            JOIN products p ON pri.product_id = p.id
            WHERE pr.user_id = ? AND pr.status = ?
            GROUP BY pr.id
            ORDER BY pr.created_at DESC
        """
        
        db.cur.execute(query, (user_id, status))
        return db.cur.fetchall()
    except Exception as e:
        logger.error(f"Error getting orders by status: {e}")
        return []

def get_order_details(order_id):
    """Get detailed order information"""
    try:
        query = """
            SELECT 
                pr.*,
                GROUP_CONCAT(
                    p.name || ' (x' || pri.quantity || ' @ ' || pri.price || ' USDT)'
                ) as items
            FROM purchase_requests pr
            JOIN purchase_request_items pri ON pr.id = pri.request_id
            JOIN products p ON pri.product_id = p.id
            WHERE pr.id = ?
            GROUP BY pr.id
        """
        
        db.cur.execute(query, (order_id,))
        result = db.cur.fetchone()
        
        if result:
            return {
                'id': result[0],
                'user_id': result[1],
                'total_amount': result[2],
                'wallet': result[3],
                'status': result[4],
                'created_at': result[5],
                'updated_at': result[6],
                'items': result[7]
            }
        return None
    except Exception as e:
        logger.error(f"Error getting order details: {e}")
        return None

async def show_orders_by_status(update: Update, context: ContextTypes.DEFAULT_TYPE, status: str):
    """Show orders filtered by status"""
    user_id = update.effective_user.id
    
    try:
        # Use direct SQL query function
        orders = get_orders_by_status(user_id, status)
        
        if not orders:
            keyboard = [[InlineKeyboardButton("🔙 Siparişlere Dön", callback_data='orders_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.callback_query.message.edit_text(
                f"{STATUS_EMOJI.get(status, '❓')} {STATUS_TEXT.get(status, status)} siparişiniz bulunmamaktadır.",
                reply_markup=reply_markup
            )
            return

        message = f"{STATUS_EMOJI.get(status, '❓')} {STATUS_TEXT.get(status, status)} Siparişleriniz:\n\n"
        keyboard = []
        
        for order in orders:
            try:
                message += f"🛍️ Sipariş #{order[0]}\n"
                message += f"📦 Ürünler:\n{order[5]}\n"
                message += f"💰 Toplam: {order[2]} USDT\n"
                message += f"📅 {order[4]}\n"
                message += f"📊 Durum: {STATUS_TEXT.get(order[3], order[3])}\n\n"
                
                # Add view details button for each order
                keyboard.append([
                    InlineKeyboardButton(
                        f"🔍 Sipariş #{order[0]} Detayları",
                        callback_data=f'view_order_{order[0]}'
                    )
                ])
            except Exception as e:
                logger.error(f"Error formatting order {order}: {e}")
                continue

        keyboard.append([InlineKeyboardButton("🔙 Siparişlere Dön", callback_data='orders_menu')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await update.callback_query.message.edit_text(
                message,
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error showing orders (message too long): {e}")
            # If message is too long, send a simplified version
            simplified_message = f"{STATUS_EMOJI.get(status, '❓')} {STATUS_TEXT.get(status, status)} Siparişleriniz\n\n"
            simplified_message += "Siparişlerinizi görüntülemek için aşağıdaki butonları kullanabilirsiniz."
            await update.callback_query.message.edit_text(
                simplified_message,
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.error(f"Error showing orders by status: {e}")
        await update.callback_query.message.edit_text(
            "Siparişler görüntülenirken bir hata oluştu.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )

async def show_order_details(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: int):
    """Show detailed information about a specific order"""
    try:
        # Get order details using direct SQL query
        order = get_order_details(order_id)
        
        if not order:
            await update.callback_query.message.edit_text(
                "❌ Sipariş bulunamadı!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Siparişlere Dön", callback_data='orders_menu')
                ]])
            )
            return

        # Format order details message
        message = f"🛍️ Sipariş #{order['id']}\n\n"
        message += f"📦 Ürünler:\n{order['items']}\n"
        message += f"💰 Toplam: {order['total_amount']} USDT\n"
        message += f"📅 Tarih: {order['created_at']}\n"
        message += f"📊 Durum: {STATUS_TEXT.get(order['status'], order['status'])}\n"

        # Add status-specific information
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