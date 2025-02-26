import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes, ConversationHandler
from config import ADMIN_ID
from states import CART_QUANTITY, SUPPORT_TICKET
from .menu import show_main_menu
from database import Database
import os

logger = logging.getLogger(__name__)
db = Database('shop.db')

async def show_products_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔍 Ürünleri Görüntüle", callback_data='view_products')],
        [InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.edit_text(
        text="🛒 Ürünler Menüsü",
        reply_markup=reply_markup
    )

async def view_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    products = db.get_products()
    
    # Delete previous messages to keep chat clean
    try:
        await update.callback_query.message.delete()
    except Exception as e:
        logger.error(f"Error deleting message: {e}")
    
    if not products:
        keyboard = [[InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Henüz ürün bulunmamaktadır.",
            reply_markup=reply_markup
        )
        return

    # Send all products in a single message
    for product in products:
        message = f"🔸 {product[1]}\n"
        message += f"📝 {product[2]}\n"
        message += f"💰 {product[3]} USDT"
        
        keyboard = [
            [InlineKeyboardButton(f"🛒 Sepete Ekle", callback_data=f'add_to_cart_{product[0]}')],
        ]
        
        # Son ürün için Ana Menü butonunu ekle
        if product == products[-1]:
            keyboard.append([InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')])
        
        try:
            if product[4] and os.path.exists(product[4]):  # Fotoğraf varsa
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=open(product[4], 'rb'),
                    caption=message,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:  # Fotoğraf yoksa
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=message,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        except Exception as e:
            logger.error(f"Error sending product {product[1]}: {e}")
            # Hata durumunda mesajı fotoğrafsız gönder
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

async def show_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cart_items = db.get_cart_items(user_id)

    # Delete current message
    try:
        await update.callback_query.message.delete()
    except Exception as e:
        logger.error(f"Error deleting message: {e}")

    # Clear any stored message IDs
    context.user_data.pop('menu_message_id', None)
    
    if not cart_items:
        keyboard = [[InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🛒 Sepetiniz boş!",
            reply_markup=reply_markup
        )
        return

    total = sum(item[2] * item[3] for item in cart_items)  # price * quantity
    total_items = sum(item[3] for item in cart_items)  # sum of quantities
    
    message = f"🛒 Sepetinizdeki Ürünler ({total_items} adet):\n\n"
    keyboard = []
    
    for item in cart_items:
        message += f"📦 {item[1]}\n"
        message += f"💰 {item[2]} USDT (x{item[3]})\n"
        message += f"Toplam: {item[2] * item[3]} USDT\n"
        keyboard.append([
            InlineKeyboardButton(f"❌ {item[1]}", callback_data=f'remove_cart_{item[0]}')
        ])
    
    message += f"\n💰 Genel Toplam: {total} USDT"
    
    if cart_items:
        keyboard.append([InlineKeyboardButton("💳 Satın Al", callback_data='request_purchase')])
    keyboard.append([InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        reply_markup=reply_markup
    )

async def handle_purchase_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Check if user is banned
    if db.is_user_banned(user_id):
        await update.callback_query.message.edit_text(
            "⛔️ Hesabınız yasaklanmıştır. Daha fazla işlem yapamazsınız.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )
        return
    
    cart_items = db.get_cart_items(user_id)
    
    if not cart_items:
        await update.callback_query.message.edit_text(
            "❌ Sepetiniz boş!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )
        return
    
    # Create purchase request
    request_id = db.create_purchase_request(user_id, cart_items)
    if not request_id:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Satın alma talebi oluşturulurken bir hata oluştu. Lütfen tekrar deneyin.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )
        return
    
    # Clear user's cart
    db.clear_user_cart(user_id)
    
    # Delete all previous messages
    try:
        await update.callback_query.message.delete()
    except Exception as e:
        logger.error(f"Error deleting message: {e}")
    
    # Notify admin
    total = sum(item[2] * item[3] for item in cart_items)
    admin_message = f"🛍️ Yeni Satın Alma Talebi #{request_id}\n\n"
    admin_message += f"👤 Kullanıcı ID: {user_id}\n"
    admin_message += "📦 Ürünler:\n"
    for item in cart_items:
        admin_message += f"- {item[1]} (x{item[3]}) - {item[2] * item[3]} USDT\n"
    admin_message += f"\n💰 Toplam: {total} USDT"
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Onayla", callback_data=f'approve_purchase_{request_id}'),
            InlineKeyboardButton("❌ Reddet", callback_data=f'reject_purchase_{request_id}'),
        ]
    ]
    
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error sending admin notification: {e}")
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="✅ Satın alma talebiniz oluşturuldu! Admin onayı bekleniyor.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
        ]])
    )
    return ConversationHandler.END

async def handle_add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Check if user is banned
    if db.is_user_banned(user_id):
        await query.message.edit_text(
            "⛔️ Hesabınız yasaklanmıştır. Daha fazla işlem yapamazsınız.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )
        return ConversationHandler.END
    
    product_id = int(query.data.split('_')[3])
    product = db.get_product(product_id)
    if not product:
        await query.message.edit_text(
            "❌ Ürün bulunamadı!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )
        return ConversationHandler.END
    
    context.user_data['adding_to_cart'] = product_id
    context.user_data['last_bot_message_id'] = query.message.message_id
    
    try:
        await query.message.edit_text(
            text=f"📦 {product[1]} için miktar giriniz:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 İptal", callback_data='view_products')
            ]])
        )
    except Exception as e:
        logger.error(f"Error editing message: {e}")
        # Mesaj düzenlenemezse yeni mesaj gönder
        sent_message = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"📦 {product[1]} için miktar giriniz:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 İptal", callback_data='view_products')
            ]])
        )
        context.user_data['last_bot_message_id'] = sent_message.message_id
        
        # Eski mesajı silmeye çalış
        try:
            await query.message.delete()
        except Exception as e:
            logger.error(f"Error deleting old message: {e}")
    
    return CART_QUANTITY

async def handle_cart_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        quantity = int(update.message.text)
        last_message_id = context.user_data.get('last_bot_message_id')
        
        if not last_message_id:
            await update.message.delete()
            return ConversationHandler.END
        
        if quantity <= 0:
            # Delete user's message
            await update.message.delete()
            
            # Edit the previous message
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=last_message_id,
                text="❌ Lütfen 0'dan büyük bir sayı girin!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 İptal", callback_data='view_products')
                ]])
            )
            return CART_QUANTITY
            
        product_id = context.user_data.get('adding_to_cart')
        if not product_id:
            await update.message.delete()
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=last_message_id,
                text="❌ Bir hata oluştu. Lütfen tekrar deneyin.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
                ]])
            )
            return ConversationHandler.END
        
        # Sepete ekle
        db.add_to_cart(update.effective_user.id, product_id, quantity)
        
        # Kullanıcının mesajını sil
        await update.message.delete()
        
        # Sepetteki toplam ürün sayısını al
        cart_count = db.get_cart_count(update.effective_user.id)
        
        # Edit previous message with success message
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=last_message_id,
            text="✅ Ürün sepete eklendi!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"🛒 Sepeti Görüntüle ({cart_count})", callback_data='show_cart')],
                [InlineKeyboardButton("🔙 Ürünlere Dön", callback_data='view_products')]
            ])
        )
        
        return ConversationHandler.END
        
    except ValueError:
        # Delete user's message
        await update.message.delete()
        
        # Edit the previous message
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=last_message_id,
            text="❌ Lütfen geçerli bir sayı girin!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 İptal", callback_data='view_products')
            ]])
        )
        return CART_QUANTITY

async def handle_support_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message.text
    
    # Delete user's message
    try:
        await update.message.delete()
    except Exception as e:
        logger.error(f"Error deleting user message: {e}")
    
    # Destek mesajını admine ilet
    admin_message = f"📩 Yeni Destek Talebi\n\n"
    admin_message += f"👤 Kullanıcı ID: {user_id}\n"
    admin_message += f"💬 Mesaj:\n{message}"
    
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_message,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )
    except Exception as e:
        logger.error(f"Error forwarding support ticket to admin: {e}")
    
    # Send success message through main menu
    await show_main_menu(
        update, 
        context, 
        "✅ Destek talebiniz başarıyla oluşturuldu. En kısa sürede size dönüş yapılacaktır."
    )
    
    return ConversationHandler.END

async def show_payment_howto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Delete previous message if exists
    try:
        await update.callback_query.message.delete()
    except Exception as e:
        logger.error(f"Error deleting message: {e}")

    message = """📜 Ödeme Nasıl Yapılır?

Binance'den başka bir cüzdana TRC20 ağıyla USDT göndermek için:

1️⃣ Binance Uygulamasını Aç 📲 ve Cüzdan → Spot Cüzdan 💰 sekmesine gir.
2️⃣ Çekme (Withdraw) 🔄 seçeneğine tıkla.
3️⃣ USDT'yi Seç 💵 ve alıcının cüzdan adresini 🏦 yapıştır.
4️⃣ Ağ olarak TRC20'yi seç 🌐 (Düşük işlem ücreti için).
5️⃣ Göndermek istediğin miktarı gir ✍️ ve Devam Et 🔜 butonuna bas.
6️⃣ İşlemi onayla ✅ (Google Authenticator/SMS/E-posta doğrulaması 📩).
7️⃣ Transfer tamamlanınca 🎉 işlem geçmişinden takibini yapabilirsin 👀.

⚠️ Dikkat: Alıcının cüzdan adresini ve ağı (TRC20) doğru seçtiğinden emin ol! 🚀"""

    keyboard = [[InlineKeyboardButton("🔙 Ödeme Menüsüne Dön", callback_data='payment_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        reply_markup=reply_markup
    )

async def show_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Delete previous message if exists
    try:
        await update.callback_query.message.delete()
    except Exception as e:
        logger.error(f"Error deleting message: {e}")

    message = """❓ S.S.S/Kurallar

📜 Genel Kurallar:
1. Adminlerle her zaman saygılı ve profesyonel iletişim kurulmalıdır
2. Spam veya kötüye kullanım yasaktır
3. Sahte ödeme bildirimi yapanlar anında yasaklanır

1️⃣ Ödeme yaptım, ne kadar beklemeliyim?
- Ödemeler ortalama 5-10 dakika içinde onaylanır

2️⃣ Hangi ödeme yöntemleri kabul ediliyor?
- Sadece USDT (TRC20) kabul edilmektedir

3️⃣ Minimum/Maksimum ödeme tutarı nedir?
- Minimum işlem tutarı: 20 USDT
- Maksimum işlem tutarı: 1000 USDT

4️⃣ Ürün teslimi nasıl yapılıyor?
- Ödeme onaylandıktan sonra ürün konumu bot tarafından teslim edilir

5️⃣ Paramı geri alabilir miyim?
- Başarılı işlemlerde iade yapılmamaktadır

⚠️ Önemli Uyarı: Üç kez üst üste reddedilen sipariş hesabınızın kalıcı olarak yasaklanmasına neden olacaktır."""

    keyboard = [[InlineKeyboardButton("🔙 Destek Menüsüne Dön", callback_data='support_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        reply_markup=reply_markup
    )