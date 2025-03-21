import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import Database
from config import ADMIN_ID, PRODUCTS_DIR
from datetime import datetime
from states import (
    PRODUCT_NAME, PRODUCT_DESCRIPTION, PRODUCT_PRICE, PRODUCT_IMAGE,
    EDIT_NAME, EDIT_DESCRIPTION, EDIT_PRICE, BROADCAST_MESSAGE,
    WALLET_INPUT
)

logger = logging.getLogger(__name__)

db = Database('shop.db')

async def handle_purchase_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Acknowledge the button click
    
    logger.debug("Starting purchase approval process")
    
    # Parse the callback data
    action = 'approve' if 'approve_purchase' in query.data else 'reject'
    request_id = int(query.data.split('_')[-1])
    request_id = int(request_id)
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
                failed_payments = db.get_failed_payments_count(request['user_id'])
            
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
            else:
                user_message = (
                    f"{status_emoji} Siparişiniz {status_text}!\n\n"
                    f"🛍️ Sipariş #{request['id']}\n\n"
                    f"📦 Ürünler:\n{request['items']}"
                    f"💰 Toplam: {request['total_amount']} USDT"
                )
            
            admin_message = (
                f"{status_emoji} Sipariş #{request['id']} {status_text}!\n\n"
                f"👤 Kullanıcı: {request['user_id']}\n"
                f"📦 Ürünler:\n{request['items']}"
                f"💰 Toplam: {request['total_amount']} USDT"
            )
            
            # Send notification to user
            logger.debug(f"Sending notification to user {request['user_id']}")
            
            # Delete previous pending messages
            try:
                async for message in context.bot.get_chat_history(request['user_id'], limit=10):
                    if message.text and (
                        "Satın alma talebiniz oluşturuldu" in message.text or
                        "Siparişiniz onaylandı" in message.text or
                        "Siparişiniz reddedildi" in message.text
                    ):
                        try:
                            await message.delete()
                        except Exception as e:
                            logger.error(f"Error deleting message: {e}")
                        break
            except Exception as e:
                logger.error(f"Error cleaning old messages: {e}")

            await context.bot.send_message(
                chat_id=request['user_id'],
                text=user_message,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
                ]])
            )
            
            logger.debug("Updating admin's message")
            # Send new admin message
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=admin_message,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
                ]])
            )
        
        except Exception as e:
            logger.exception(f"Detailed error in purchase approval process: {str(e)}")
            logger.error(f"Request data during error: {request}")
            await query.message.edit_text(
                "❌ İşlem sırasında bir hata oluştu.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
                ]])
            )
    else:
        logger.error(f"Failed to update request #{request_id} status to {status}")
        await query.message.edit_text(
            "❌ Durum güncellenirken bir hata oluştu.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )

async def show_pending_purchases(update: Update, context: ContextTypes.DEFAULT_TYPE):
    requests = db.get_pending_purchase_requests()
    
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
            text="Bekleyen satın alma talebi bulunmamaktadır.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )
        return
    
    message = "🛍️ Bekleyen Satın Alma Talepleri:\n\n"
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
    
    keyboard = []
    for request in requests:
        keyboard.append([
            InlineKeyboardButton("✅ Onayla", callback_data=f'approve_purchase_{request[0]}'),
            InlineKeyboardButton("❌ Reddet", callback_data=f'reject_purchase_{request[0]}')
        ])
    keyboard.append([InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        reply_markup=reply_markup
    )

async def admin_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    products = db.get_products()
    keyboard = [
        [InlineKeyboardButton("➕ Ürün Ekle", callback_data='add_product')]
    ]
    
    # Add edit and delete buttons for each product
    for product in products:
        keyboard.append([
            InlineKeyboardButton(f"✏️ {product[1]}", callback_data=f'edit_product_{product[0]}'),
            InlineKeyboardButton("❌", callback_data=f'delete_product_{product[0]}')
        ])
    
    keyboard.append(
        [InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]
        )
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.edit_text("Ürün Yönetimi:", reply_markup=reply_markup)

async def handle_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Ürün adını kaydet
    context.user_data['product_data'] = {'name': update.message.text}
    
    # Yeni mesaj gönder
    sent_message = await update.message.reply_text(
        "Lütfen ürün açıklamasını girin:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 İptal", callback_data='admin_products')
        ]])
    )
    
    # Mesaj ID'sini sakla
    context.user_data['current_message_id'] = sent_message.message_id
    
    # Kullanıcının mesajını sil
    await update.message.delete()
    
    return PRODUCT_DESCRIPTION

async def handle_product_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Açıklamayı kaydet
    context.user_data['product_data']['description'] = update.message.text
    
    # Önceki mesajı sil
    current_message_id = context.user_data.get('current_message_id')
    if current_message_id:
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=current_message_id
            )
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
    
    # Yeni mesaj gönder
    sent_message = await update.message.reply_text(
        "Lütfen ürün fiyatını USDT olarak girin (sadece sayı):",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 İptal", callback_data='admin_products')
        ]])
    )
    
    # Yeni mesaj ID'sini sakla
    context.user_data['current_message_id'] = sent_message.message_id
    
    # Kullanıcının mesajını sil
    await update.message.delete()
    
    return PRODUCT_PRICE

async def handle_product_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text)
        context.user_data['product_data']['price'] = price
        
        # Önceki mesajı sil
        current_message_id = context.user_data.get('current_message_id')
        if current_message_id:
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=current_message_id
                )
            except Exception as e:
                logger.error(f"Error deleting message: {e}")
        
        # Yeni mesaj gönder
        sent_message = await update.message.reply_text(
            "Lütfen ürün fotoğrafını gönderin:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 İptal", callback_data='admin_products')
            ]])
        )
        
        # Yeni mesaj ID'sini sakla
        context.user_data['current_message_id'] = sent_message.message_id
        
        # Kullanıcının mesajını sil
        await update.message.delete()
        
        return PRODUCT_IMAGE
    except ValueError:
        # Hata mesajı gönder
        sent_message = await update.message.reply_text(
            "❌ Lütfen geçerli bir sayı girin:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 İptal", callback_data='admin_products')
            ]])
        )
        
        # Yeni mesaj ID'sini sakla
        context.user_data['current_message_id'] = sent_message.message_id
        
        # Kullanıcının mesajını sil
        await update.message.delete()
        
        return PRODUCT_PRICE

async def handle_product_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        try:
            product_data = context.user_data['product_data']
            product_dir = os.path.join(PRODUCTS_DIR, product_data['name'])
            os.makedirs(product_dir, exist_ok=True)
            
            photo = update.message.photo[-1]
            photo_file = await context.bot.get_file(photo.file_id)
            image_path = os.path.join(product_dir, 'product.jpg')
            await photo_file.download_to_drive(image_path)
            
            success = db.add_product(
                product_data['name'],
                product_data['description'],
                product_data['price'],
                image_path
            )
            
            del context.user_data['product_data']
            
            if success:
                keyboard = [[InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text("✅ Ürün başarıyla eklendi!", reply_markup=reply_markup)
            else:
                await update.message.reply_text("❌ Ürün eklenirken bir hata oluştu. Lütfen tekrar deneyin.")
            
            return ConversationHandler.END
        except Exception as e:
            logger.error(f"Error adding product: {e}")
            await update.message.reply_text("❌ Ürün eklenirken bir hata oluştu. Lütfen tekrar deneyin.")
            return ConversationHandler.END
    else:
        await update.message.reply_text("Lütfen bir fotoğraf gönderin:")
        return PRODUCT_IMAGE

async def handle_edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    product_id = context.user_data.get('edit_product_id')
    if not product_id:
        await update.message.reply_text("❌ Bir hata oluştu. Lütfen tekrar deneyin.")
        return ConversationHandler.END
    
    new_name = update.message.text
    db.update_product_name(product_id, new_name)
    
    keyboard = [[InlineKeyboardButton("🔙 Ürün Yönetimine Dön", callback_data='admin_products')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("✅ Ürün adı başarıyla güncellendi!", reply_markup=reply_markup)
    
    return ConversationHandler.END

async def handle_edit_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    product_id = context.user_data.get('edit_product_id')
    if not product_id:
        await update.message.reply_text("❌ Bir hata oluştu. Lütfen tekrar deneyin.")
        return ConversationHandler.END
    
    new_description = update.message.text
    db.update_product_description(product_id, new_description)
    
    keyboard = [[InlineKeyboardButton("🔙 Ürün Yönetimine Dön", callback_data='admin_products')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("✅ Ürün açıklaması başarıyla güncellendi!", reply_markup=reply_markup)
    
    return ConversationHandler.END

async def handle_edit_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    product_id = context.user_data.get('edit_product_id')
    if not product_id:
        await update.message.reply_text("❌ Bir hata oluştu. Lütfen tekrar deneyin.")
        return ConversationHandler.END
    
    try:
        new_price = float(update.message.text)
        db.update_product_price(product_id, new_price)
        
        keyboard = [[InlineKeyboardButton("🔙 Ürün Yönetimine Dön", callback_data='admin_products')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("✅ Ürün fiyatı başarıyla güncellendi!", reply_markup=reply_markup)
        
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Lütfen geçerli bir sayı girin:")
        return EDIT_PRICE

async def handle_edit_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    product_id = int(query.data.split('_')[2])
    context.user_data['edit_product_id'] = product_id
    
    # Get product details
    product = db.get_product(product_id)
    if not product:
        await query.message.edit_text("❌ Ürün bulunamadı!")
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton("✏️ Ürün Adını Düzenle", callback_data=f'edit_name_{product_id}')],
        [InlineKeyboardButton("📝 Açıklamayı Düzenle", callback_data=f'edit_desc_{product_id}')],
        [InlineKeyboardButton("💰 Fiyatı Düzenle", callback_data=f'edit_price_{product_id}')],
        [InlineKeyboardButton("🔙 Geri Dön", callback_data='admin_products')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = f"📦 {product[1]}\n"
    message += f"📝 {product[2]}\n"
    message += f"💰 {product[3]} USDT\n\n"
    message += "Düzenlemek istediğiniz alanı seçin:"
    
    await query.message.edit_text(message, reply_markup=reply_markup)
    return ConversationHandler.END

async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send broadcast message to all users"""
    message = update.message.text
    user_id = update.effective_user.id

    # Clear any stored message IDs
    context.user_data.pop('menu_message_id', None)
    
    # Only allow admin to broadcast
    if user_id != ADMIN_ID:
        logger.warning(f"Non-admin user {user_id} tried to broadcast")
        return ConversationHandler.END
    
    # Delete all previous messages
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
    
    logger.info(f"Starting broadcast to {len(users)} users")
    success_count = 0

    for user_id in users:
        try:
            logger.debug(f"Sending broadcast to user {user_id}")
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
            logger.error(f"Failed to send broadcast to user {user_id}: {e}")
            continue

    # Send success message
    success_message = f"✅ Bildirim {success_count}/{len(users)} kullanıcıya gönderildi!"
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=success_message,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
        ]])
    )
    logger.info(f"Broadcast completed: {success_message}")

    return ConversationHandler.END

async def show_users_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the user management menu"""
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
        
        # Add ban/unban button for each user
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

async def show_wallet_pool(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the wallet pool management menu"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("➕ Cüzdan Ekle", callback_data='add_wallet')],
        [InlineKeyboardButton("📋 Cüzdan Listesi", callback_data='list_wallets')],
        [InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]
    ]
    
    await query.message.edit_text(
        "👛 Cüzdan Havuzu Yönetimi",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def add_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a new wallet to the pool"""
    query = update.callback_query
    await query.answer()
    
    await query.message.edit_text(
        "🏦 Yeni TRC20 cüzdan adresini girin:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 İptal", callback_data='admin_wallets')
        ]])
    )
    return WALLET_INPUT

async def handle_wallet_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the wallet address input"""
    wallet_address = update.message.text.strip()
    
    # Delete user's message
    try:
        await update.message.delete()
    except Exception as e:
        logger.error(f"Error deleting message: {e}")
    
    # Basic validation for TRC20 address
    if not wallet_address.startswith('T') or len(wallet_address) != 34:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Geçersiz TRC20 cüzdan adresi! Lütfen tekrar deneyin.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Cüzdan Havuzuna Dön", callback_data='admin_wallets')
            ]])
        )
        return ConversationHandler.END
    
    # Add wallet to database
    db.add_wallet(wallet_address)
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="✅ Cüzdan başarıyla eklendi!",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Cüzdan Havuzuna Dön", callback_data='admin_wallets')
        ]])
    )
    return ConversationHandler.END

async def list_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of all wallets in the pool"""
    query = update.callback_query
    await query.answer()
    
    wallets = db.get_all_wallets()
    if not wallets:
        await query.message.edit_text(
            "❌ Havuzda cüzdan bulunmamaktadır.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Cüzdan Havuzuna Dön", callback_data='admin_wallets')
            ]])
        )
        return
    
    message = "📋 Cüzdan Listesi:\n\n"
    keyboard = []
    
    for wallet in wallets:
        status = "🔴 Kullanımda" if wallet[2] else "🟢 Müsait"
        message += f"🏦 {wallet[1][:8]}...{wallet[1][-8:]}\n"
        message += f"📊 Durum: {status}\n"
        message += "───────────────\n"
        
        if not wallet[2]:  # If wallet is not in use
            keyboard.append([
                InlineKeyboardButton(
                    f"❌ Sil ({wallet[1][:8]}...)",
                    callback_data=f'delete_wallet_{wallet[0]}'
                )
            ])
    
    keyboard.append([InlineKeyboardButton("🔙 Cüzdan Havuzuna Dön", callback_data='admin_wallets')])
    
    try:
        await query.message.edit_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error showing wallets: {e}")
        # If message is too long, send a simplified version
        simplified_message = "📋 Cüzdan Listesi\n\nCüzdanları yönetmek için aşağıdaki butonları kullanın:"
        await query.message.edit_text(
            simplified_message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def handle_user_ban_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle toggling user ban status"""
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
    await show_users_menu(update, context)