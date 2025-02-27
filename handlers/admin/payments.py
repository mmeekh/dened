import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import Database
import logging
from config import LOCATIONS_DIR
import os

logger = logging.getLogger(__name__)
db = Database('shop.db')

# handlers/admin/payments.py düzeltilmiş handle_purchase_approval fonksiyonu

async def handle_purchase_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle purchase request approval/rejection"""
    query = update.callback_query
    await query.answer()  # Acknowledge the button click
    
    logger.debug("Starting purchase approval process")
    
    # Parse the callback data
    action = 'approve' if 'approve_purchase' in query.data else 'reject'
    request_id = int(query.data.split('_')[-1])
    logger.info(f"Processing {action} for request #{request_id}")
    
    # Set status based on action
    status = 'completed' if action == 'approve' else 'rejected'
    status_emoji = "✅" if status == 'completed' else "❌"
    status_text = "onaylandı" if status == 'completed' else "reddedildi"
    
    # Get request details before updating status
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

    # Update request status
    if db.update_purchase_request_status(request_id, status):
        try:
            # Delete current message
            try:
                await query.message.delete()
            except Exception as e:
                logger.error(f"Error deleting message: {e}")
            
            # Get user's failed payments count if rejected
            failed_payments = 0
            if status == 'rejected':
                try:
                    cursor = db.conn.cursor()
                    cursor.execute(
                        "SELECT failed_payments FROM users WHERE telegram_id = ?",
                        (request['user_id'],)
                    )
                    result = cursor.fetchone()
                    if result and result[0] is not None:
                        failed_payments = result[0]
                        logger.info(f"User {request['user_id']} has {failed_payments} failed payments")
                except Exception as e:
                    logger.error(f"Error getting failed payments: {e}")
            
            logger.debug(f"Successfully updated request #{request_id} status to {status}")
            
            # Prepare messages
            if status == 'rejected':
                warning = ""
                if failed_payments >= 3:
                    warning = "\n\n⛔️ Hesabınız yasaklanmıştır!"
                elif failed_payments == 2:
                    warning = "\n\n⚠️ SON UYARI: Bir sonraki başarısız ödemede hesabınız yasaklanacaktır! ⚠️"
                else:
                    warning = f"\n\n⚠️ Not: {3 - failed_payments} başarısız ödeme hakkınız kaldı."
                
                user_message = (
                    f"{status_emoji} Siparişiniz {status_text}!\n\n"
                    f"🛍️ Sipariş #{request['id']}\n\n"
                    f"📦 Ürünler:\n{request['items']}"
                    f"💰 Toplam: {request['total_amount']} USDT"
                    f"{warning}"
                )
                
                # Kullanıcıya bildirim gönder
                logger.info(f"Sending rejection notification to user {request['user_id']}")
                try:
                    await context.bot.send_message(
                        chat_id=request['user_id'],
                        text=user_message,
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
                        ]])
                    )
                    logger.info(f"Successfully sent rejection notification to user {request['user_id']}")
                except Exception as e:
                    logger.error(f"Error sending rejection notification to user {request['user_id']}: {e}")
            else:
                # Onaylanan siparişteki ürünü bul
                try:
                    logger.debug(f"Fetching product for request {request_id}")
                    
                    # Get product_id from purchase_request_items
                    result = db.execute("""
                        SELECT product_id 
                        FROM purchase_request_items 
                        WHERE request_id = ? 
                        LIMIT 1""",
                        (request_id,)
                    )
                    
                    if not result or len(result) == 0:
                        logger.error(f"No products found for request #{request_id}")
                        raise Exception("No products found in request")
                    
                    # İlk sonucu al
                    product_id = result[0][0]
                    logger.debug(f"Found product ID: {product_id} for request {request_id}")
                    
                    # Ürün için müsait konum bul
                    location_path = db.get_available_location(product_id)
                    logger.debug(f"Location path: {location_path} for product {product_id}")
                    
                    if location_path and os.path.exists(location_path):
                        # Konum fotoğrafını gönder
                        logger.info(f"Sending location photo {location_path} to user {request['user_id']}")
                        await context.bot.send_photo(
                            chat_id=request['user_id'],
                            photo=open(location_path, 'rb'),
                            caption=f"✅ Siparişiniz onaylandı!\n\n"
                                    f"🛍️ Sipariş #{request['id']}\n"
                                    f"💰 Toplam: {request['total_amount']} USDT\n\n"
                                    f"📍 Konum bilgileri yukarıdaki fotoğrafta yer almaktadır.",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
                            ]])
                        )
                        logger.info(f"Successfully sent location photo to user {request['user_id']}")
                    else:
                        # Konum yoksa normal mesaj gönder
                        logger.warning(f"No location found for product {product_id}")
                        user_message = (
                            f"{status_emoji} Siparişiniz {status_text}!\n\n"
                            f"🛍️ Sipariş #{request['id']}\n\n"
                            f"📦 Ürünler:\n{request['items']}"
                            f"💰 Toplam: {request['total_amount']} USDT\n\n"
                            f"⚠️ Konum bilgisi yakında gönderilecektir."
                        )
                        await context.bot.send_message(
                            chat_id=request['user_id'],
                            text=user_message,
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
                            ]])
                        )
                        logger.info(f"Sent text notification to user {request['user_id']} (no location available)")
                except Exception as e:
                    logger.exception(f"Error sending location: {e}")
                    user_message = (
                        f"{status_emoji} Siparişiniz {status_text}!\n\n"
                        f"🛍️ Sipariş #{request['id']}\n\n"
                        f"📦 Ürünler:\n{request['items']}"
                        f"💰 Toplam: {request['total_amount']} USDT\n\n"
                        f"⚠️ Konum bilgisi yakında gönderilecektir."
                    )
                    try:
                        await context.bot.send_message(
                            chat_id=request['user_id'],
                            text=user_message,
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
                            ]])
                        )
                        logger.info(f"Sent fallback text notification to user {request['user_id']}")
                    except Exception as nested_e:
                        logger.error(f"Error sending fallback notification to user {request['user_id']}: {nested_e}")
            
            # Admin için mesaj
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
            logger.exception(f"Detailed error in purchase approval process: {str(e)}")
            logger.error(f"Request data during error: {request}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ İşlem sırasında bir hata oluştu.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
                ]])
            )
    else:
        logger.error(f"Failed to update request #{request_id} status to {status}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Durum güncellenirken bir hata oluştu.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Tekrar Dene", callback_data=f'{action}_purchase_{request_id}')],
                [InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]
            ])
        )

async def show_pending_purchases(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pending purchase requests and order management options"""
    try:
        # Get all pending requests using direct SQL query
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
        
        # Delete current message and clear stored IDs
        try:
            await update.callback_query.message.delete()
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
        
        # Clear any stored message IDs
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
        # Get order counts for each status
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