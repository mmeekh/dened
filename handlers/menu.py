import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config import ADMIN_ID, PRODUCTS_DIR
from states import PRODUCT_NAME, PRODUCT_DESCRIPTION, PRODUCT_PRICE, PRODUCT_IMAGE, EDIT_NAME, EDIT_DESCRIPTION, EDIT_PRICE, BROADCAST_MESSAGE, SUPPORT_TICKET, CART_QUANTITY
from database import Database
from utils.menu_utils import show_generic_menu

logger = logging.getLogger(__name__)
db = Database('shop.db')

def get_main_menu_keyboard(user_id):
    """Kullanıcının rolüne göre ana menü klavyesini oluşturur"""
    if user_id == ADMIN_ID:
        try:
            db.cur.execute("SELECT COUNT(*) FROM purchase_requests WHERE status = 'pending'")
            pending_count = db.cur.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting pending orders count: {e}")
            pending_count = 0
            
        keyboard = [
            [InlineKeyboardButton("🎯 Ürün Yönetimi", callback_data='admin_products')],
            [InlineKeyboardButton("👥 Kullanıcı Yönetimi", callback_data='admin_users')],
            [InlineKeyboardButton(f"📋 Sipariş Yönetimi ({pending_count})", callback_data='admin_payments')],
            [InlineKeyboardButton("📢 Bildirim Gönder", callback_data='send_broadcast')],
            [
                InlineKeyboardButton("👛 Cüzdan Havuzu", callback_data='admin_wallets'),
                InlineKeyboardButton("📍 Konum Havuzu", callback_data='admin_locations')
            ],
        ]
    else:
        try:
            cart_count = db.get_cart_count(user_id)
            cart_text = f"🛍 Sepetim ({cart_count})" if cart_count > 0 else "🛍 Sepetim"
        except Exception as e:
            logger.error(f"Error getting cart count: {e}")
            cart_text = "🛍 Sepetim"

        keyboard = [
            [InlineKeyboardButton("🎯 Ürünler", callback_data='products_menu')],
            [InlineKeyboardButton(cart_text, callback_data='show_cart')],
            [InlineKeyboardButton("🏷 Siparişlerim", callback_data='orders_menu')],
            [InlineKeyboardButton("💳 Ödeme İşlemleri", callback_data='payment_menu')],
            [InlineKeyboardButton("ℹ️ Destek & Bilgi", callback_data='support_menu')],
            [InlineKeyboardButton("🎮 Flappy Weed Oyna", callback_data='games_menu')],

        ]
    return InlineKeyboardMarkup(keyboard)

async def show_main_menu(update, context, message=None):
    """Ana menüyü gösterir - menünün sabit kalması için aynı mesajı düzenler"""
    user_id = update.effective_user.id
    text = message if message else 'Hoş geldiniz! Lütfen bir seçenek seçin:'
    reply_markup = get_main_menu_keyboard(user_id)
    
    # Genel menü şablonunu kullan
    await show_generic_menu(
        update=update,
        context=context,
        text=text,
        reply_markup=reply_markup
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Karşılama mesajını göster ve ana menüyü oluştur"""
    try:
        # Kullanıcı bilgilerini al
        user_first_name = update.effective_user.first_name if update.effective_user.first_name else "Değerli Müşterimiz"
        user_id = update.effective_user.id
        
        # Kullanıcı yasaklı mı kontrol et
        if db.is_user_banned(user_id):
            # Genel menü şablonunu kullan
            await show_generic_menu(
                update=update,
                context=context, 
                text="⛔️ Hesabınız yasaklanmıştır. Daha fazla işlem yapamazsınız.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Çıkış", callback_data='exit')
                ]])
            )
            return ConversationHandler.END
        
        logger.info("Starting new conversation")
        # Kullanıcıyı veritabanına ekle
        logger.info(f"Adding user {user_id} to database")
        if db.add_user(user_id):
            logger.info(f"Successfully added user {user_id}")
        else:
            logger.warning(f"Failed to add user {user_id} or user already exists")
        
        # Karşılama mesajını oluştur
        welcome_message = f"""🌟 Tobacco'ya Hoş Geldiniz {user_first_name}! 🌟

🎯 Premium kalite ürünlerimiz ve güvenilir hizmetimizle sizlere en iyi deneyimi sunmaktan gurur duyuyoruz.

✨ Neden Biz?
• 💯 %100 Orijinal Ürünler
• 🔒 Güvenli Alışveriş
• 🚀 Hızlı Teslimat
• 💎 Premium Hizmet

Menüden istediğiniz seçeneği seçerek alışverişe başlayabilirsiniz."""
        
        # Ana menüyü göster
        await show_main_menu(update, context, welcome_message)
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        # Hata durumunda basit bir mesaj göster
        await show_generic_menu(
            update=update,
            context=context,
            text="Hoş geldiniz! Lütfen bir seçenek seçin:",
            reply_markup=get_main_menu_keyboard(user_id)
        )
        logger.error(f"Fallback message sent for user {user_id}")
        return ConversationHandler.END