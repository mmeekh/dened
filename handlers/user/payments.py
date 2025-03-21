import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from utils.exchange import get_usdt_try_rate
from utils.menu_utils import cleanup_old_messages
from database import Database
from config import ADMIN_ID
import qrcode
from telegram.error import BadRequest
import random
from io import BytesIO

logger = logging.getLogger(__name__)
db = Database('shop.db')
wallet = None

async def safely_delete_message(bot, chat_id, message_id):
    """Safely delete a message, handling the case where message doesn't exist"""
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        return True
    except BadRequest as e:
        if "Message to delete not found" in str(e):
            return False
        else:
            logger.error(f"BadRequest error deleting message: {e}")
            return False
    except Exception as e:
        logger.error(f"Error deleting message: {e}")
        return False
async def show_payment_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show payment menu with improved message cleanup"""
    try:
        # Clean up old messages
        await cleanup_old_messages(
            context.bot, 
            update.effective_chat.id, 
            context=context
        )
        
        # Store message IDs with consistent naming to be tracked for future cleanup
        if update.callback_query and update.callback_query.message:
            context.user_data['payment_prev_message_id'] = update.callback_query.message.message_id
    
    except Exception as e:
        logger.error(f"Error in message cleanup: {e}")
    keyboard = [
        [InlineKeyboardButton("📜 Ödeme Nasıl Yapılır", callback_data='payment_howto')],
        [InlineKeyboardButton("📱 QR Kod ile Ödeme", callback_data='show_qr_code')],
        [InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    context.user_data['last_payment_message'] = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="💳 Ödeme İşlemleri",
        reply_markup=reply_markup
    )
async def handle_purchase_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle purchase request creation with discount application"""
    logger.info("Starting purchase request process")
    user_id = update.effective_user.id
    
    if db.is_user_banned(user_id):
        logger.warning(f"Banned user {user_id} attempted to create purchase request")
        await update.callback_query.message.edit_text(
            "⛔️ Hesabınız yasaklanmıştır. Daha fazla işlem yapamazsınız.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )
        return
    
    cart_items = db.get_cart_items(user_id)
    
    if not cart_items:
        logger.warning(f"User {user_id} attempted purchase with empty cart")
        await update.callback_query.message.edit_text(
            "❌ Sepetiniz boş!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )
        return
    
    # Calculate total
    subtotal = sum(item[2] * item[3] for item in cart_items)
    total = subtotal
    logger.info(f"Cart total for user {user_id}: {total} USDT")
    
    # Apply discount if available
    discount_info = context.user_data.get('active_discount')
    discount_text = ""
    discount_percent = 0
    coupon_id = None
    
    if discount_info and discount_info.get('valid'):
        discount_percent = discount_info.get('discount_percent', 0)
        coupon_id = discount_info.get('coupon_id')
        discount_amount = (subtotal * discount_percent) / 100
        total = subtotal - discount_amount
        discount_text = f"\n🏷️ İndirim: %{discount_percent} (-{discount_amount:.2f} USDT)"
        logger.info(f"Applied discount: {discount_percent}%, new total: {total} USDT")
    
    if total < 20:
        logger.warning(f"User {user_id} order below minimum (Total: {total} USDT)")
        await update.callback_query.message.edit_text(
            "❌ Minimum sipariş tutarı 20 USDT'dir.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Sepete Dön", callback_data='show_cart')
            ]])
        )
        return
    
    if total > 1000:
        logger.warning(f"User {user_id} order above maximum (Total: {total} USDT)")
        await update.callback_query.message.edit_text(
            "❌ Maksimum sipariş tutarı 1000 USDT'dir.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Sepete Dön", callback_data='show_cart')
            ]])
        )
        return
    
    # First find wallet without transaction
    wallet = None
    active_request = db.get_user_active_request(user_id)
    if active_request and active_request.get('wallet'):
        wallet = active_request.get('wallet')
        logger.info(f"Reusing existing wallet {wallet} for user {user_id}")
    else:
        logger.info(f"Assigning permanent wallet to user {user_id}")
        wallet = db.assign_wallet_to_user(user_id)
        
        if not wallet:
            logger.error("No available wallet found")
            await update.callback_query.message.edit_text(
                """❌ Şu anda uygun cüzdan bulunmamaktadır.

Lütfen daha sonra tekrar deneyin veya destek ekibiyle iletişime geçin.""",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
                ]])
            )
            return
    
    logger.info(f"Using wallet {wallet} for purchase request")
    
    # Now handle the purchase request manually in a transaction
    request_id = None
    try:
        # Calculate final total amount
        total_amount = subtotal
        if discount_percent > 0:
            discount_amount = (subtotal * discount_percent) / 100
            total_amount = subtotal - discount_amount
            
        # Start a transaction manually
        db.cur.execute("BEGIN TRANSACTION")
        
        # 1. Insert into purchase_requests table
        db.cur.execute(
            """INSERT INTO purchase_requests 
               (user_id, total_amount, wallet, status, discount_percent) 
               VALUES (?, ?, ?, 'pending', ?)""",
            (user_id, total_amount, wallet, discount_percent)
        )
        request_id = db.cur.lastrowid
        
        # 2. Insert items into purchase_request_items table
        for item in cart_items:
            db.cur.execute(
                """INSERT INTO purchase_request_items 
                   (request_id, product_id, quantity, price) 
                   VALUES (?, ?, ?, ?)""",
                (request_id, item[4], item[3], item[2])
            )
        
        # 3. Apply coupon if used
        if coupon_id:
            db.cur.execute(
                "UPDATE discount_coupons SET is_used = 1 WHERE id = ?",
                (coupon_id,)
            )
            # Clear discount from user_data
            if 'active_discount' in context.user_data:
                del context.user_data['active_discount']
        
        # 4. Clear the cart
        db.cur.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        
        # Commit the transaction
        db.conn.commit()
        logger.info(f"Successfully created purchase request #{request_id}")
        
    except Exception as e:
        # Something went wrong - try to rollback
        try:
            db.conn.rollback()
            logger.error(f"Transaction rolled back: {str(e)}")
        except Exception as rollback_error:
            logger.error(f"Error during rollback: {str(rollback_error)}")
        
        # Show error message to user
        await update.callback_query.message.edit_text(
            "❌ İşlem sırasında bir hata oluştu. Lütfen tekrar deneyin.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )
        return
    
    # Notify admin with discount information
    admin_message = f"🛍️ Yeni Satın Alma Talebi #{request_id}\n\n"
    admin_message += f"👤 Kullanıcı ID: {user_id}\n"
    admin_message += "📦 Ürünler:\n"
    
    for item in cart_items:
        admin_message += f"- {item[1]} (x{item[3]}) - {item[2] * item[3]} USDT\n"
    
    admin_message += f"\n💰 Alt Toplam: {subtotal} USDT"
    
    if discount_percent > 0:
        admin_message += f"\n🏷️ İndirim: %{discount_percent} (-{(subtotal * discount_percent / 100):.2f} USDT)"
    
    admin_message += f"\n💵 Ödenecek Tutar: {total} USDT"
    admin_message += f"\n🏦 Cüzdan: {wallet}"
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Onayla", callback_data=f'approve_purchase_{request_id}'),
            InlineKeyboardButton("❌ Reddet", callback_data=f'reject_purchase_{request_id}')
        ]
    ]
    
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        logger.info(f"Sent purchase notification to admin for request #{request_id}")
    except Exception as e:
        logger.error(f"Error sending admin notification: {e}")
    
    # User confirmation with discount information
    try:
        await update.callback_query.message.delete()
    except Exception as e:
        logger.error(f"Error deleting message: {e}")
    
    caption = f"""✅ Satın alma talebiniz oluşturuldu!

🛍️ Sipariş #{request_id}
💰 Toplam Tutar: {subtotal} USDT"""

    if discount_percent > 0:
        discount_amount = subtotal * discount_percent / 100
        caption += f"\n🏷️ İndirim: %{discount_percent} (-{discount_amount:.2f} USDT)"
        caption += f"\n💵 Ödenecek Tutar: {total} USDT"

    caption += f"""

🏦 TRC20 Cüzdan Adresi:
<code>{wallet}</code>

⚠️ Önemli Hatırlatmalar:
- Sadece TRC20 ağını kullanın!
- Tam tutarı tek seferde gönderin
- QR kodu Binance uygulamasında okutabilirsiniz
- Ödeme sonrası 5-10 dk bekleyin
- Farklı tutar/ağ kullanmayın!

👤 Bu cüzdan sizin için ayrılmıştır, tüm ödemelerinizde aynı adresi kullanacaksınız."""
    
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Cüzdanı Kopyala", callback_data=f'copy_wallet_{wallet}')],
        [InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]
    ])
    
    # Generate QR code
    qr_image = None
    try:
        import qrcode
        from io import BytesIO
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=5
        )
        qr.add_data(wallet)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        bio = BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        qr_image = bio
    except Exception as e:
        logger.error(f"Error generating QR code: {e}")
    
    try:
        if qr_image:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=qr_image,
                caption=caption,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=caption,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.error(f"Error sending confirmation message: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"✅ Sipariş #{request_id} oluşturuldu! Ödeme bilgileri için lütfen sipariş detaylarınızı kontrol edin.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )
    
    return ConversationHandler.END
async def show_wallet_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show wallet address for manual payment"""
    user_id = update.effective_user.id
    active_request = db.get_user_active_request(user_id)
    
    if not active_request:
        await update.callback_query.message.edit_text(
            "❌ Aktif ödeme talebiniz bulunmamaktadır.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ödeme Menüsü", callback_data='payment_menu')
            ]])
        )
        return
    
    wallet = active_request.get('wallet')
    if not wallet:
        await update.callback_query.message.edit_text(
            "❌ Henüz cüzdan ataması yapılmamış.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ödeme Menüsü", callback_data='payment_menu')
            ]])
        )
        return
    
    message = f"""🏦 Ödeme Bilgileri

💰 Ödenecek Tutar: {active_request['total_amount']} USDT
📝 Sipariş No: #{active_request['id']}

📦 Ürünler:
{active_request['items']}

🔸 TRC20 Cüzdan Adresi:
<code>{wallet}</code>

⚠️ Önemli Hatırlatmalar:
• Sadece TRC20 ağını kullanın!
• Tam tutarı tek seferde gönderin
• Ödeme sonrası 5-10 dk bekleyin
• Farklı tutar/ağ kullanmayın!"""
    
    keyboard = [
        [InlineKeyboardButton("📋 Cüzdanı Kopyala", callback_data=f'copy_wallet_{wallet}')],
        [InlineKeyboardButton("🔙 Ödeme Menüsü", callback_data='payment_menu')]
    ]
    
    try:
        await update.callback_query.message.edit_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error showing wallet address: {e}")
        await update.callback_query.message.edit_text(
            "❌ Cüzdan bilgileri gösterilirken bir hata oluştu.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ödeme Menüsü", callback_data='payment_menu')
            ]])
        )
async def show_payment_howto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show payment instructions with proper message cleanup"""
    try:
        if update.callback_query and update.callback_query.message:
            await safely_delete_message(
                context.bot,
                update.effective_chat.id,
                update.callback_query.message.message_id
            )
                
        last_message = context.user_data.get('last_payment_message')
        if last_message and hasattr(last_message, 'message_id'):
            await safely_delete_message(
                context.bot,
                update.effective_chat.id,
                last_message.message_id
            )
            context.user_data.pop('last_payment_message', None)
    except Exception as e:
        logger.error(f"Error in message cleanup: {e}")
    
    usdt_try_rate = get_usdt_try_rate()
    exchange_rate_text = f" (≈ {20 * usdt_try_rate:.2f} ₺)" if usdt_try_rate else ""
    max_exchange_text = f" (≈ {1000 * usdt_try_rate:.2f} ₺)" if usdt_try_rate else ""

    message = f"""📜 Ödeme Nasıl Yapılır?

💡 Ödeme Yöntemleri:
1. QR Kod ile Hızlı Ödeme
2. Manuel Cüzdan Adresi ile Ödeme

📱 QR Kod ile Ödeme:
• "QR Kod ile Ödeme" butonuna tıklayın
• Binance uygulamasında QR kodu okutun
• Tutarı girin ve onaylayın

🏦 Manuel Ödeme:
Binance'den başka bir cüzdana TRC20 ağıyla USDT göndermek için:

1️⃣ Binance Uygulamasını Aç 📲 ve Cüzdan → Spot Cüzdan 💰 sekmesine gir.
2️⃣ Çekme (Withdraw) 🔄 seçeneğine tıkla.
3️⃣ USDT'yi Seç 💵 ve alıcının cüzdan adresini 🏦 yapıştır.
4️⃣ Ağ olarak TRC20'yi seç 🌐 (Düşük işlem ücreti için).
5️⃣ Göndermek istediğin miktarı gir ✍️ ve Devam Et 🔜 butonuna bas.
6️⃣ İşlemi onayla ✅ (Google Authenticator/SMS/E-posta doğrulaması 📩).
7️⃣ Transfer tamamlanınca 🎉 işlem geçmişinden takibini yapabilirsin 👀.

⚠️ Önemli Notlar:
• Minimum işlem tutarı: 20 USDT{exchange_rate_text}
• Maksimum işlem tutarı: 1000 USDT{max_exchange_text}
• Sadece TRC20 ağı kabul edilmektedir
• Yanlış ağ seçimi durumunda iade yapılmaz
• Ödeme onayı genellikle 5-10 dakika içinde gerçekleşir

⚠️ Dikkat: Alıcının cüzdan adresini ve ağı (TRC20) doğru seçtiğinden emin ol! 🚀"""

    keyboard = [[InlineKeyboardButton("🔙 Ödeme Menüsüne Dön", callback_data='payment_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    context.user_data['last_payment_message'] = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        reply_markup=reply_markup
    )
async def show_qr_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show QR code for payment with wallet address even without active request"""
    user_id = update.effective_user.id
    
    # Clean up previous messages
    try:
        if update.callback_query and update.callback_query.message:
            await safely_delete_message(
                context.bot,
                update.effective_chat.id,
                update.callback_query.message.message_id
            )
        
        last_message = context.user_data.get('last_payment_message')
        if last_message and hasattr(last_message, 'message_id'):
            await safely_delete_message(
                context.bot,
                update.effective_chat.id,
                last_message.message_id
            )
            context.user_data.pop('last_payment_message', None)
    except Exception as e:
        logger.error(f"Error in message cleanup: {e}")
    
    # First try to get the user's wallet from user_wallets table
    wallet = db.get_user_wallet(user_id)
    
    # If no wallet is assigned yet, assign one now
    if not wallet:
        wallet = db.assign_wallet_to_user(user_id)
        logger.info(f"Assigned new permanent wallet {wallet} to user {user_id}")
        
    # If we still don't have a wallet, handle the error
    if not wallet:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Cüzdan atanırken bir hata oluştu. Lütfen daha sonra tekrar deneyin.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ödeme Menüsüne Dön", callback_data='payment_menu')
            ]])
        )
        return
    
    try:        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(wallet)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        bio = BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        
        # Simplified message as requested
        message = f"""🏦 TRC20 Cüzdan Adresi:
<code>{wallet}</code>

⚠️ Önemli Hatırlatmalar:
- Sadece TRC20 ağını kullanın!
- Tam tutarı tek seferde gönderin
- QR kodu Binance uygulamasında okutabilirsiniz
- Ödeme sonrası 5-10 dk bekleyin
- Farklı tutar/ağ kullanmayın!

👤 Bu cüzdan sizin için ayrılmıştır, tüm ödemelerinizde aynı adresi kullanacaksınız."""
        
        context.user_data['last_payment_message'] = await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=bio,
            caption=message,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Ödeme Menüsüne Dön", callback_data='payment_menu')]
            ]),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Error generating QR code: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ QR kod oluşturulurken bir hata oluştu.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ödeme Menüsüne Dön", callback_data='payment_menu')
            ]])
        )
async def check_payment_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check payment status for active request"""
    user_id = update.effective_user.id
    
    # Get user's active purchase request
    active_request = db.get_user_active_request(user_id)
    
    if not active_request:
        await update.callback_query.message.edit_text(
            "❌ Aktif ödeme talebiniz bulunmamaktadır.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ödeme Menüsüne Dön", callback_data='payment_menu')
            ]])
        )
        return
    
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
    
    message = f"""🔍 Ödeme Durumu

🛍️ Sipariş #{active_request['id']}
💰 Toplam: {active_request['total_amount']} USDT
📊 Durum: {status_emoji[active_request['status']]} {status_text[active_request['status']]}
📅 Tarih: {active_request['created_at']}

📦 Ürünler:
{active_request['items']}"""

    if active_request['status'] == 'pending':
        message += """
⏳ Ödemeniz kontrol ediliyor...
• Ödeme yaptıysanız lütfen bekleyin
• Ortalama onay süresi: 5-10 dakika
• Durumu buradan takip edebilirsiniz"""
        
        keyboard = [
            [InlineKeyboardButton("🔄 Durumu Güncelle", callback_data='check_payment_status')],
            [InlineKeyboardButton("🔙 Ödeme Menüsüne Dön", callback_data='payment_menu')]
        ]
    else:
        keyboard = [[InlineKeyboardButton("🔙 Ödeme Menüsüne Dön", callback_data='payment_menu')]]
    
    await update.callback_query.message.edit_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
