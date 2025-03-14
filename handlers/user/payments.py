import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from utils.exchange import get_usdt_try_rate
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
    """Show payment menu with proper message cleanup"""
    try:
        # Check if we're coming from a callback query (button press)
        if update.callback_query:
            # Try to delete the message that contains the button that was pressed
            if update.callback_query.message:
                await safely_delete_message(
                    context.bot, 
                    update.effective_chat.id, 
                    update.callback_query.message.message_id
                )
                
        # Try to delete last payment message if it exists
        last_message = context.user_data.get('last_payment_message')
        if last_message:
            if hasattr(last_message, 'message_id'):
                await safely_delete_message(
                    context.bot,
                    update.effective_chat.id,
                    last_message.message_id
                )
            # Clear the stored message reference
            context.user_data.pop('last_payment_message', None)
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
    total = sum(item[2] * item[3] for item in cart_items)
    logger.info(f"Cart total for user {user_id}: {total} USDT")
    
    # Apply discount if available
    discount_info = context.user_data.get('active_discount')
    discount_text = ""
    discount_percent = 0
    coupon_id = None
    
    if discount_info and discount_info.get('valid'):
        discount_percent = discount_info.get('discount_percent', 0)
        coupon_id = discount_info.get('coupon_id')
        discount_amount = (total * discount_percent) / 100
        total = total - discount_amount
        discount_text = f"\n💯 İndirim: %{discount_percent} (-{discount_amount:.2f} USDT)"
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
    
    wallet = None
    
    active_request = db.get_user_active_request(user_id)
    if active_request and active_request.get('wallet'):
        wallet = active_request.get('wallet')
        logger.info(f"Reusing existing wallet {wallet} for user {user_id}")
    else:
        # Burada get_available_wallet yerine assign_wallet_to_user kullanıyoruz
        # Böylece kullanıcıya kalıcı olarak bir cüzdan atanacak
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
    
    # Create purchase request with discount info
    request_id = db.create_purchase_request(user_id, cart_items, wallet, discount_percent)
    if not request_id:
        logger.error(f"Failed to create purchase request for user {user_id}")
        await update.callback_query.message.edit_text(
            "❌ Satın alma talebi oluşturulurken bir hata oluştu. Lütfen tekrar deneyin.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )
        return
    
    logger.info(f"Created purchase request #{request_id} for user {user_id}")
    
    # Mark coupon as used if applicable
    if coupon_id:
        db.apply_discount_coupon(coupon_id)
        # Clear the active discount from user_data
        if 'active_discount' in context.user_data:
            del context.user_data['active_discount']
    
    # Clear cart
    db.clear_user_cart(user_id)
    logger.info(f"Cleared cart for user {user_id}")
    
    # Rest of your existing handle_purchase_request function...
    
    # Notify admin with discount information
    admin_message = f"🛍️ Yeni Satın Alma Talebi #{request_id}\n\n"
    admin_message += f"👤 Kullanıcı ID: {user_id}\n"
    admin_message += "📦 Ürünler:\n"
    
    subtotal = sum(item[2] * item[3] for item in cart_items)
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
• Sadece TRC20 ağını kullanın!
• Tam tutarı tek seferde gönderin
• QR kodu Binance uygulamasında okutabilirsiniz
• Ödeme sonrası 5-10 dk bekleyin
• Farklı tutar/ağ kullanmayın!

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
    """Show QR code for payment with wallet address for copy"""
    user_id = update.effective_user.id
    
    active_request = db.get_user_active_request(user_id)
    
    if not active_request:
        await update.callback_query.message.edit_text(
            "❌ Aktif ödeme talebiniz bulunmamaktadır.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ödeme Menüsüne Dön", callback_data='payment_menu')
            ]])
        )
        return
    
    wallet = db.get_request_wallet(active_request['id'])
    if not wallet:
        await update.callback_query.message.edit_text(
            "❌ Henüz cüzdan ataması yapılmamış.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ödeme Menüsüne Dön", callback_data='payment_menu')
            ]])
        )
        return
    
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
        
        usdt_try_rate = get_usdt_try_rate()
        exchange_rate_text = f" (≈ {20 * usdt_try_rate:.2f} ₺ + transfer ücreti)" if usdt_try_rate else ""
        max_exchange_text = f" (≈ {1000 * usdt_try_rate:.2f} ₺ + transfer ücreti)" if usdt_try_rate else ""

        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(wallet)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        bio = BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        
        total_try = f" (≈ {active_request['total_amount'] * usdt_try_rate:.2f} ₺ + transfer ücreti)" if usdt_try_rate else ""
        message = f"""📱 QR Kod ile Ödeme

💰 Ödenecek Tutar: {active_request['total_amount']} USDT{total_try}
📝 Sipariş No: #{active_request['id']}

🔸 TRC20 Cüzdan Adresi:
<code>{wallet}</code>

⚠️ Önemli Hatırlatmalar:
• QR kodu Binance uygulamasında okutun
• Sadece TRC20 ağını kullanın!
• Tam tutarı tek seferde gönderin
• Minimum işlem tutarı: 20 USDT{exchange_rate_text}
• Ödeme sonrası 5-10 dk bekleyin"""
        
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
