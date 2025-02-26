import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import Database
from config import ADMIN_ID
import qrcode
import random
from io import BytesIO

logger = logging.getLogger(__name__)
db = Database('shop.db')
wallet = None

async def show_payment_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show payment menu"""
    try:
        await update.callback_query.message.delete()
    except Exception as e:
        logger.error(f"Error deleting message: {e}")

    keyboard = [
        [InlineKeyboardButton("📜 Ödeme Nasıl Yapılır", callback_data='payment_howto')],
        [InlineKeyboardButton("🔍 Ödeme Durumu", callback_data='check_payment_status')],
        [InlineKeyboardButton("📱 QR Kod ile Ödeme", callback_data='show_qr_code')],
        [InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="💳 Ödeme İşlemleri",
        reply_markup=reply_markup
    )
# handlers/user/payments.py dosyasına bu fonksiyonu ekleyin
async def handle_purchase_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle purchase request creation with single message output"""
    logger.info("Starting purchase request process")
    user_id = update.effective_user.id
    
    # Kullanıcının yasaklı olup olmadığını kontrol et
    if db.is_user_banned(user_id):
        logger.warning(f"Banned user {user_id} attempted to create purchase request")
        await update.callback_query.message.edit_text(
            "⛔️ Hesabınız yasaklanmıştır. Daha fazla işlem yapamazsınız.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )
        return
    
    # Sepeti kontrol et
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
    
    # Toplam tutarı hesapla
    total = sum(item[2] * item[3] for item in cart_items)
    logger.info(f"Cart total for user {user_id}: {total} USDT")
    
    # Minimum ve maksimum limitleri kontrol et
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
    
    # Cüzdan atama işlemi - Geliştirilmiş Versiyon
    wallet = None
    
    # 1. Önce kullanıcının mevcut aktif siparişine atanmış bir cüzdan var mı kontrol et
    active_request = db.get_user_active_request(user_id)
    if active_request and active_request.get('wallet'):
        wallet = active_request.get('wallet')
        logger.info(f"Reusing existing wallet {wallet} for user {user_id}")
    else:
        # 2. Tüm kullanılabilir cüzdanları kontrol et
        logger.info("Checking for available wallets")
        available_wallets = db.get_available_wallet_count()
        logger.info(f"Found {available_wallets} available wallets")
        
        # 3. Kullanılabilir cüzdan yoksa, bazı cüzdanları serbest bırak
        if available_wallets == 0:
            logger.warning("No available wallets, attempting to free up wallets")
            try:
                # Aktif siparişlerde kullanılmayan cüzdanları serbest bırak
                db.conn.execute("""
                    UPDATE wallets SET in_use = 0
                    WHERE address NOT IN (
                        SELECT wallet FROM purchase_requests WHERE status = 'pending'
                    )
                """)
                db.conn.commit()
                logger.info("Reset some wallets to available state")
            except Exception as e:
                logger.error(f"Error resetting wallets: {e}")
        
        # 4. Şimdi bir cüzdan almayı dene
        wallet = db.get_available_wallet()
        
        # 5. Hala cüzdan yoksa, yeni bir tane ekle (acil durum)
        if not wallet:
            logger.error("Still no available wallet found, creating emergency wallet")
            emergency_wallet = "T" + "".join([str(random.randint(1, 9)) for _ in range(33)])
            
            try:
                db.add_wallet(emergency_wallet)
                logger.info(f"Added emergency wallet: {emergency_wallet}")
                wallet = emergency_wallet
            except Exception as e:
                logger.error(f"Error adding emergency wallet: {e}")
        
    # Hala cüzdan yoksa, kullanıcıya bilgi ver
    if not wallet:
        logger.error("Failed to get or create a wallet for purchase")
        await update.callback_query.message.edit_text(
            """❌ Şu anda uygun cüzdan bulunmamaktadır.

Lütfen daha sonra tekrar deneyin veya destek ekibiyle iletişime geçin.""",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )
        return
    
    logger.info(f"Using wallet {wallet} for purchase request")
    
    # Satın alma talebi oluştur
    request_id = db.create_purchase_request(user_id, cart_items, wallet)
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
    
    # Sepeti temizle
    db.clear_user_cart(user_id)
    logger.info(f"Cleared cart for user {user_id}")
    
    # Admini bilgilendir
    admin_message = f"🛍️ Yeni Satın Alma Talebi #{request_id}\n\n"
    admin_message += f"👤 Kullanıcı ID: {user_id}\n"
    admin_message += "📦 Ürünler:\n"
    
    for item in cart_items:
        admin_message += f"- {item[1]} (x{item[3]}) - {item[2] * item[3]} USDT\n"
    
    admin_message += f"\n💰 Toplam: {total} USDT"
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
    
    # QR kodunu oluştur
    qr_image = None
    try:
        # QR kodu oluştur
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=5
        )
        qr.add_data(wallet)
        qr.make(fit=True)
        
        # Resim oluştur
        img = qr.make_image(fill_color="black", back_color="white")
        bio = BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        qr_image = bio
        logger.info(f"QR code successfully generated for wallet {wallet}")
    except Exception as e:
        logger.error(f"Error generating QR code: {e}")
        qr_image = None
        
    # Orijinal mesajı sil ve yerine yeni mesaj gönder
    try:
        await update.callback_query.message.delete()
    except Exception as e:
        logger.error(f"Error deleting message: {e}")
    
    # Kullanıcıya sadece bir mesaj içinde hem QR kod hem de bilgileri gönder
    caption = f"""✅ Satın alma talebiniz oluşturuldu!

🛍️ Sipariş #{request_id}
💰 Toplam Tutar: {total} USDT

🏦 TRC20 Cüzdan Adresi:
<code>{wallet}</code>

⚠️ Önemli Hatırlatmalar:
• Sadece TRC20 ağını kullanın!
• Tam tutarı tek seferde gönderin
• QR kodu Binance uygulamasında okutabilirsiniz
• Ödeme sonrası 5-10 dk bekleyin
• Farklı tutar/ağ kullanmayın!"""

    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Cüzdanı Kopyala", callback_data=f'copy_wallet_{wallet}')],
        [InlineKeyboardButton("🔍 Ödeme Durumu", callback_data='check_payment_status')],
        [InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]
    ])
    
    try:
        if qr_image:
            # QR kod oluşturulduysa, fotoğraflı mesaj gönder
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=qr_image,
                caption=caption,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            logger.info(f"Sent purchase confirmation with QR code to user {user_id}")
        else:
            # QR kod oluşturulamadıysa, sadece metin gönder
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=caption,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            logger.info(f"Sent purchase confirmation without QR code to user {user_id}")
    except Exception as e:
        logger.error(f"Error sending confirmation message: {e}")
        # Mesaj gönderme hatası durumunda son bir deneme daha yap
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"✅ Sipariş #{request_id} oluşturuldu! Toplam: {total} USDT",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
                ]])
            )
        except Exception as e2:
            logger.error(f"Final error sending fallback message: {e2}")
    
    logger.info(f"Purchase request process completed for user {user_id}")
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
- Sadece TRC20 ağını kullanın!
- Tam tutarı tek seferde gönderin
- Ödeme sonrası 5-10 dk bekleyin
- Farklı tutar/ağ kullanmayın!"""
    
    keyboard = [
        [InlineKeyboardButton("📋 Cüzdanı Kopyala", callback_data=f'copy_wallet_{wallet}')],
        [InlineKeyboardButton("🔍 Ödeme Durumu", callback_data='check_payment_status')],
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
    """Show payment instructions"""
    try:
        await update.callback_query.message.delete()
    except Exception as e:
        logger.error(f"Error deleting message: {e}")

    message = """📜 Ödeme Nasıl Yapılır?

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
• Minimum işlem tutarı: 20 USDT
• Maksimum işlem tutarı: 1000 USDT
• Sadece TRC20 ağı kabul edilmektedir
• Yanlış ağ seçimi durumunda iade yapılmaz
• Ödeme onayı genellikle 5-10 dakika içinde gerçekleşir
• "Ödeme Durumu" butonundan işleminizi takip edebilirsiniz

⚠️ Dikkat: Alıcının cüzdan adresini ve ağı (TRC20) doğru seçtiğinden emin ol! 🚀"""

    keyboard = [[InlineKeyboardButton("🔙 Ödeme Menüsüne Dön", callback_data='payment_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        reply_markup=reply_markup
    )

async def show_qr_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show QR code for payment"""
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
    
    # Get assigned wallet
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
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(wallet)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        bio = BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        
        # Send QR code with payment info
        message = f"""📱 QR Kod ile Ödeme

💰 Ödenecek Tutar: {active_request['total_amount']} USDT
📝 Sipariş No: #{active_request['id']}

⚠️ Önemli Hatırlatmalar:
• QR kodu Binance uygulamasında okutun
• Sadece TRC20 ağını kullanın!
• Tam tutarı tek seferde gönderin
• Ödeme sonrası 5-10 dk bekleyin"""
        
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=bio,
            caption=message,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 Ödeme Durumu", callback_data='check_payment_status')],
                [InlineKeyboardButton("🔙 Ödeme Menüsüne Dön", callback_data='payment_menu')]
            ])
        )
        
    except Exception as e:
        logger.error(f"Error generating QR code: {e}")
        await update.callback_query.message.edit_text(
            "❌ QR kod oluşturulurken bir hata oluştu.",
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
