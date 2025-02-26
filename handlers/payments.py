import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import Database
import qrcode
from io import BytesIO
from datetime import datetime

logger = logging.getLogger(__name__)
db = Database('shop.db')

async def show_payment_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show payment menu"""
    keyboard = [
        [
            InlineKeyboardButton("📱 QR Kod ile Ödeme", callback_data='show_qr_code'),
            InlineKeyboardButton("🏦 Manuel Ödeme", callback_data='show_wallet')
        ],
        [
            InlineKeyboardButton("🔍 Ödeme Durumu", callback_data='check_payment_status'),
            InlineKeyboardButton("📜 Nasıl Ödeme Yaparım?", callback_data='payment_howto')
        ],
        [InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(
        """💳 Ödeme İşlemleri

Ödeme yapmak için tercih ettiğiniz yöntemi seçin:

📱 QR Kod ile Ödeme
• Hızlı ve kolay
• Binance uygulaması ile tarama
• Otomatik adres doldurma

🏦 Manuel Ödeme
• Cüzdan adresini kopyalama
• İstediğiniz cüzdan/uygulama
• Detaylı talimatlar

⚠️ Önemli Hatırlatmalar:
• Sadece TRC20 ağını kullanın
• Minimum işlem: 20 USDT
• Maksimum işlem: 1000 USDT""",
        reply_markup=reply_markup
    )

async def show_qr_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show QR code for payment"""
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
    
    wallet = db.get_request_wallet(active_request['id'])
    if not wallet:
        await update.callback_query.message.edit_text(
            "❌ Henüz cüzdan ataması yapılmamış.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ödeme Menüsü", callback_data='payment_menu')
            ]])
        )
        return
    
    try:
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(wallet)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        bio = BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        
        message = f"""📱 QR Kod ile Ödeme

💰 Ödenecek Tutar: {active_request['total_amount']} USDT
📝 Sipariş No: #{active_request['id']}

📦 Ürünler:
{active_request['items']}

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
                [InlineKeyboardButton("🔙 Ödeme Menüsü", callback_data='payment_menu')]
            ])
        )
        
    except Exception as e:
        logger.error(f"Error generating QR code: {e}")
        await update.callback_query.message.edit_text(
            "❌ QR kod oluşturulurken bir hata oluştu.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ödeme Menüsü", callback_data='payment_menu')
            ]])
        )

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
    
    wallet = db.get_request_wallet(active_request['id'])
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

async def check_payment_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check payment status"""
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
            [InlineKeyboardButton("🔙 Ödeme Menüsü", callback_data='payment_menu')]
        ]
    else:
        keyboard = [[InlineKeyboardButton("🔙 Ödeme Menüsü", callback_data='payment_menu')]]
    
    await update.callback_query.message.edit_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )