import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import Database
import logging
from config import LOCATIONS_DIR
import os

logger = logging.getLogger(__name__)
db = Database('shop.db')

async def handle_purchase_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle purchase request approval/rejection with improved structure"""
    query = update.callback_query
    await query.answer()  # Acknowledge the button click
    
    logger.debug("Starting purchase approval process")
    
    # Parse action and request ID from callback data
    action = 'approve' if 'approve_purchase' in query.data else 'reject'
    request_id = int(query.data.split('_')[-1])
    logger.info(f"Processing {action} for request #{request_id}")
    
    # Determine status information
    status = 'completed' if action == 'approve' else 'rejected'
    status_emoji = "✅" if status == 'completed' else "❌"
    status_text = "onaylandı" if status == 'completed' else "reddedildi"
    
    # Get request details
    request = db.get_purchase_request(request_id)
    logger.debug(f"Retrieved request data: {request}")
    
    if not request:
        logger.error(f"Request #{request_id} not found in database")
        await query.message.edit_text(
            "❌ Sipariş bulunamadı.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )
        return

    # Update request status in database
    if not db.update_purchase_request_status(request_id, status):
        logger.error(f"Failed to update request #{request_id} status to {status}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Durum güncellenirken bir hata oluştu.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Tekrar Dene", callback_data=f'{action}_purchase_{request_id}')],
                [InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]
            ])
        )
        return

    # Status updated successfully, proceed with notifications
    try:
        # Try to delete the original message to keep chat clean
        try:
            await query.message.delete()
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
        
        # STEP 1: PREPARE USER NOTIFICATION
        
        if status == 'rejected':
            # Handle rejection case
            failed_payments = get_user_failed_payments(request['user_id'])
            
            # Determine warning level based on failed payments
            warning = ""
            if failed_payments >= 3:
                warning = "\n\n⛔️ Hesabınız yasaklanmıştır!"
            elif failed_payments == 2:
                warning = "\n\n⚠️ SON UYARI: Bir sonraki başarısız ödemede hesabınız yasaklanacaktır! ⚠️"
            else:
                warning = f"\n\n⚠️ Not: {3 - failed_payments} başarısız ödeme hakkınız kaldı."
            
            # Create rejection message
            user_message = (
                f"{status_emoji} Siparişiniz {status_text}!\n\n"
                f"🛍️ Sipariş #{request['id']}\n\n"
                f"📦 Ürünler:\n{request['items']}"
                f"💰 Toplam: {request['total_amount']} USDT"
                f"{warning}"
            )
            
            # Send rejection notification to user
            logger.info(f"Sending rejection notification to user {request['user_id']}")
            success = await send_user_notification(
                context.bot, 
                request['user_id'], 
                user_message,
                has_location=False
            )
            # Don't try to access message_id on the boolean result
        else:
            # Handle approval case
            await handle_approval_notification(context.bot, request)

        admin_message = (
            f"{status_emoji} Sipariş #{request['id']} {status_text}!\n\n"
            f"👤 Kullanıcı: {request['user_id']}\n"
            f"📦 Ürünler:\n{request['items']}\n"
            f"💰 Toplam: {request['total_amount']} USDT\n"
            f"🏦 Cüzdan: {request['wallet']}\n"
            f"📅 Tarih: {request['created_at']}"
        )
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=admin_message,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )
        logger.info(f"Sent confirmation message to admin for request #{request_id}")
    
    except Exception as e:
        logger.exception(f"Error in purchase approval process: {str(e)}")
        # Send error message to admin
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ İşlem sırasında bir hata oluştu.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )
def get_user_failed_payments(user_id):
    """Get user's failed payment count safely"""
    try:
        db.cur.execute(
            "SELECT failed_payments FROM users WHERE telegram_id = ?",
            (user_id,)
        )
        result = db.cur.fetchone()
        if result and result[0] is not None:
            return result[0]
        return 0
    except Exception as e:
        logger.error(f"Error getting failed payments: {e}")
        return 0

async def send_user_notification(bot, user_id, message, has_location=False, location_path=None):
    """Send notification to user with stored message tracking"""
    try:
        last_message_id = db.get_user_last_notification(user_id)
        
        if last_message_id:
            try:
                await bot.delete_message(chat_id=user_id, message_id=last_message_id)
                logger.debug(f"Deleted previous notification message {last_message_id} for user {user_id}")
            except Exception as e:
                logger.debug(f"Could not delete previous notification: {e}")
        
        new_message = None
        if has_location and location_path:
            new_message = await bot.send_photo(
                chat_id=user_id,
                photo=open(location_path, 'rb'),
                caption=message,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
                ]])
            )
            logger.info(f"Sent location photo to user {user_id}")
        else:
            new_message = await bot.send_message(
                chat_id=user_id,
                text=message,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
                ]])
            )
            logger.info(f"Sent notification message to user {user_id}")
        
        if new_message:
            db.store_user_last_notification(user_id, new_message.message_id)
            
        return True  # Başarılı gönderim durumunu işaret et
    except Exception as e:
        logger.error(f"Error sending notification to user {user_id}: {e}")
        return False  # Başarısız gönderim durumunu işaret et

async def handle_approval_notification(bot, request):
    """Handle the approval notification with location if available"""
    try:
        # Get the product ID for this request
        db.cur.execute("""
            SELECT product_id 
            FROM purchase_request_items 
            WHERE request_id = ? 
            LIMIT 1""",
            (request['id'],)
        )
        result = db.cur.fetchone()
        
        if not result or len(result) == 0:
            logger.error(f"No products found for request #{request['id']}")
            raise Exception("No products found in request")
        
        product_id = result[0]
        logger.debug(f"Found product ID: {product_id} for request {request['id']}")
        
        location_path = db.get_available_location(product_id)
        previous_message_id = db.get_user_last_notification(request['user_id'])
        if previous_message_id:
            try:
                await bot.delete_message(chat_id=request['user_id'], message_id=previous_message_id)
                logger.debug(f"Deleted previous notification {previous_message_id} for user {request['user_id']}")
            except Exception as e:
                logger.debug(f"Could not delete previous notification: {e}")
        
        if location_path and os.path.exists(location_path):
            message = (f"✅ Siparişiniz onaylandı!\n\n"
                      f"🛍️ Sipariş #{request['id']}\n"
                      f"💰 Toplam: {request['total_amount']} USDT\n\n"
                      f"📍 Konum bilgileri yukarıdaki fotoğrafta yer almaktadır.")
            
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
            new_message = await bot.send_photo(
                chat_id=request['user_id'],
                photo=open(location_path, 'rb'),
                caption=message,
                reply_markup=keyboard
            )
            
            # Store the new message ID for tracking
            if new_message:
                db.store_user_last_notification(request['user_id'], new_message.message_id)
            
            # Delete the location file after sending
            try:
                os.remove(location_path)
                logger.info(f"Location file deleted: {location_path}")
                
                # If directory is empty, remove it too
                directory = os.path.dirname(location_path)
                if os.path.exists(directory) and not os.listdir(directory):
                    os.rmdir(directory)
                    logger.info(f"Empty location directory removed: {directory}")
            except Exception as e:
                logger.error(f"Error deleting location file: {e}")
                
            return True
        else:
            # Send text-only notification if no location available
            logger.warning(f"No location found for product {product_id}")
            message = (
                f"✅ Siparişiniz onaylandı!\n\n"
                f"🛍️ Sipariş #{request['id']}\n\n"
                f"📦 Ürünler:\n{request['items']}"
                f"💰 Toplam: {request['total_amount']} USDT\n\n"
                f"⚠️ Konum bilgisi yakında gönderilecektir."
            )
            
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
            
            new_message = await bot.send_message(
                chat_id=request['user_id'],
                text=message,
                reply_markup=keyboard
            )
            
            # Store the new message ID for tracking
            if new_message:
                db.store_user_last_notification(request['user_id'], new_message.message_id)
            
            return True
            
    except Exception as e:
        logger.exception(f"Error handling approval notification: {e}")
        # Fallback message
        message = (
            f"✅ Siparişiniz onaylandı!\n\n"
            f"🛍️ Sipariş #{request['id']}\n\n"
            f"📦 Ürünler:\n{request['items']}"
            f"💰 Toplam: {request['total_amount']} USDT\n\n"
            f"⚠️ Konum bilgisi yakında gönderilecektir."
        )
        
        try:
            new_message = await bot.send_message(
                chat_id=request['user_id'],
                text=message,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
                ]])
            )
            
            # Store fallback message ID
            if new_message:
                db.store_user_last_notification(request['user_id'], new_message.message_id)
                
        except Exception as nested_e:
            logger.error(f"Error sending fallback notification: {nested_e}")
            
        return False
    
async def show_pending_purchases(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pending purchase requests and order management options"""
    try:
        db.cur.execute("""
            SELECT 
                pr.id,
                pr.user_id,
                pr.total_amount,
                pr.created_at,
                GROUP_CONCAT(
                    p.name || ' (x' || pri.quantity || ' @ ' || pri.price || ' USDT)'
                ) as items
            FROM purchase_requests pr
            JOIN purchase_request_items pri ON pr.id = pri.request_id
            JOIN products p ON pri.product_id = p.id
            WHERE pr.status = 'pending'
            GROUP BY pr.id
            ORDER BY pr.created_at DESC
        """)
        requests = db.cur.fetchall()
        
        try:
            await update.callback_query.message.delete()
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
        
        context.user_data.pop('menu_message_id', None)
        
        if not requests:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="📋 Sipariş Yönetimi\n\n⚠️ Bekleyen satın alma talebi bulunmamaktadır.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📊 Tüm Siparişler", callback_data='view_all_orders')],
                    [InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]
                ])
            )
            return
        
        message = "📋 Sipariş Yönetimi - Bekleyen Talepler\n\n"
        keyboard = []
        
        for request in requests:
            request_id = request[0]
            user_id = request[1]
            total_amount = request[2]
            created_at = request[3]
            items = request[4]
            
            message += f"🛍️ Sipariş #{request_id}\n"
            message += f"👤 Kullanıcı: {user_id}\n"
            message += f"📦 Ürünler:\n{items}"
            message += f"💰 Toplam: {total_amount} USDT\n"
            message += f"📅 Tarih: {created_at}\n\n"
        
        for request in requests:
            keyboard.append([
                InlineKeyboardButton("✅ Onayla", callback_data=f'approve_purchase_{request[0]}'),
                InlineKeyboardButton("❌ Reddet", callback_data=f'reject_purchase_{request[0]}')
            ])
        
        keyboard.append([InlineKeyboardButton("📊 Tüm Siparişler", callback_data='view_all_orders')])
        keyboard.append([InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error showing pending purchases: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Sipariş bilgileri görüntülenirken bir hata oluştu.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )

async def view_all_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View all orders with filters for admin"""
    try:
        db.cur.execute("SELECT status, COUNT(*) FROM purchase_requests GROUP BY status")
        status_counts = {status: count for status, count in db.cur.fetchall()}
        
        pending_count = status_counts.get('pending', 0)
        completed_count = status_counts.get('completed', 0)
        rejected_count = status_counts.get('rejected', 0)
        total_count = sum(status_counts.values())
        
        message = f"""📊 Tüm Siparişler

Toplam: {total_count} sipariş

Durum Dağılımı:
• ⏳ Bekleyen: {pending_count}
• ✅ Tamamlanan: {completed_count}
• ❌ Reddedilen: {rejected_count}

Görüntülemek istediğiniz sipariş türünü seçin:"""

        keyboard = [
            [InlineKeyboardButton(f"⏳ Bekleyen Siparişler ({pending_count})", callback_data='admin_pending_orders')],
            [InlineKeyboardButton(f"✅ Tamamlanan Siparişler ({completed_count})", callback_data='admin_completed_orders')],
            [InlineKeyboardButton(f"❌ Reddedilen Siparişler ({rejected_count})", callback_data='admin_rejected_orders')],
            [InlineKeyboardButton("🗑️ Siparişleri Temizle", callback_data='confirm_cleanup_orders')],
            [InlineKeyboardButton("🔙 Sipariş Yönetimine Dön", callback_data='admin_payments')],
            [InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]
        ]
        
        await update.callback_query.message.edit_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error showing all orders: {e}")
        await update.callback_query.message.edit_text(
            "❌ Siparişler görüntülenirken bir hata oluştu.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )
async def show_admin_orders_by_status(update: Update, context: ContextTypes.DEFAULT_TYPE, status: str):
    """Show all orders of a specific status for admin"""
    try:
        # Get orders with the specified status
        db.cur.execute("""
            SELECT 
                pr.id,
                pr.user_id,
                pr.total_amount,
                pr.created_at,
                pr.updated_at,
                GROUP_CONCAT(
                    p.name || ' (x' || pri.quantity || ' @ ' || pri.price || ' USDT)'
                ) as items
            FROM purchase_requests pr
            JOIN purchase_request_items pri ON pr.id = pri.request_id
            JOIN products p ON pri.product_id = p.id
            WHERE pr.status = ?
            GROUP BY pr.id
            ORDER BY pr.created_at DESC
        """, (status,))
        
        orders = db.cur.fetchall()
        
        status_emoji = {
            'pending': '⏳',
            'completed': '✅',
            'rejected': '❌'
        }
        
        status_text = {
            'pending': 'Bekleyen',
            'completed': 'Tamamlanan',
            'rejected': 'Reddedilen'
        }
        
        if not orders:
            await update.callback_query.message.edit_text(
                f"{status_emoji.get(status, '❓')} {status_text.get(status, status)} sipariş bulunmamaktadır.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Sipariş Yönetimine Dön", callback_data='admin_payments')
                ]])
            )
            return
        
        message = f"{status_emoji.get(status, '❓')} {status_text.get(status, status)} Siparişler:\n\n"
        keyboard = []
        
        for order in orders:
            order_id = order[0]
            user_id = order[1]
            total_amount = order[2]
            created_at = order[3]
            items = order[5]
            
            message += f"🛍️ Sipariş #{order_id}\n"
            message += f"👤 Kullanıcı: {user_id}\n"
            message += f"📦 Ürünler:\n{items}"
            message += f"💰 Toplam: {total_amount} USDT\n"
            message += f"📅 Tarih: {created_at}\n\n"
            
            if status == 'pending':
                keyboard.append([
                    InlineKeyboardButton("✅ Onayla", callback_data=f'approve_purchase_{order_id}'),
                    InlineKeyboardButton("❌ Reddet", callback_data=f'reject_purchase_{order_id}')
                ])
        
        keyboard.append([InlineKeyboardButton("🔙 Tüm Siparişler", callback_data='view_all_orders')])
        keyboard.append([InlineKeyboardButton("🔙 Sipariş Yönetimine Dön", callback_data='admin_payments')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await update.callback_query.message.edit_text(
                message,
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error showing orders: {e}")
            # If message is too long, send a simplified version
            simplified_message = f"{status_emoji.get(status, '❓')} {status_text.get(status, status)} Siparişler\n\n"
            simplified_message += f"Toplam {len(orders)} sipariş bulunmaktadır.\n\n"
            simplified_message += "Siparişleri görüntülemek için aşağıdaki butonları kullanabilirsiniz."
            await update.callback_query.message.edit_text(
                simplified_message,
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"Error showing orders by status: {e}")
        await update.callback_query.message.edit_text(
            "❌ Siparişler gösterilirken bir hata oluştu.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Sipariş Yönetimine Dön", callback_data='admin_payments')
            ]])
        )