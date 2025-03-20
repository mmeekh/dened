import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config import ADMIN_ID, PRODUCTS_DIR,BOT_PASSWORD
from states import PASSWORD_VERIFICATION,PRODUCT_NAME, PRODUCT_DESCRIPTION, PRODUCT_PRICE, PRODUCT_IMAGE, EDIT_NAME, EDIT_DESCRIPTION, EDIT_PRICE, BROADCAST_MESSAGE, SUPPORT_TICKET, CART_QUANTITY
from database import Database
from utils.menu_utils import show_generic_menu


logger = logging.getLogger(__name__)
db = Database('shop.db')

WELCOME_MESSAGE_TEMPLATE = """🌟 Tobacco'ya Hoş Geldiniz {}! 🌟

🎯 Premium kalite ürünlerimiz ve güvenilir hizmetimizle sizlere en iyi deneyimi sunmaktan gurur duyuyoruz.

✨ Neden Biz?
- 💯 %100 Orijinal Ürünler
- 🔒 Güvenli Alışveriş
- 🚀 Hızlı Teslimat
- 💎 Premium Hizmet

Menüden istediğiniz seçeneği seçerek alışverişe başlayabilirsiniz."""

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
            
            # Kullanıcının kupon sayısını al
            coupon_count = get_user_coupon_count(user_id)
            coupon_text = f"🎟️ Kuponlarım ({coupon_count})" if coupon_count > 0 else "🎟️ Kuponlarım"
        except Exception as e:
            logger.error(f"Error getting counts: {e}")
            cart_text = "🛍 Sepetim"
            coupon_text = "🎟️ Kuponlarım"

        keyboard = [
            [
                InlineKeyboardButton("🎯 Ürünler", callback_data='products_menu'),
                InlineKeyboardButton(cart_text, callback_data='show_cart')
            ],
            [
                InlineKeyboardButton("🏷 Siparişlerim", callback_data='orders_menu'),
                InlineKeyboardButton(coupon_text, callback_data='my_coupons')
            ],
            [InlineKeyboardButton("💳 Ödeme İşlemleri", callback_data='payment_menu')],
            [InlineKeyboardButton("ℹ️ Destek & Bilgi", callback_data='support_menu')],
            [InlineKeyboardButton("🎮 Flappy Weed Oyna", callback_data='games_menu')],
        ]
    return InlineKeyboardMarkup(keyboard)

def get_user_coupon_count(user_id):
    """Kullanıcının aktif kupon sayısını döndürür"""
    try:
        db.cur.execute(
            """SELECT COUNT(*) 
               FROM discount_coupons 
               WHERE user_id = ? AND is_used = 0 
                 AND (expires_at IS NULL OR expires_at > datetime('now'))""",
            (user_id,)
        )
        result = db.cur.fetchone()
        return result[0] if result else 0
    except Exception as e:
        logger.error(f"Error getting coupon count: {e}")
        return 0
async def show_main_menu(update, context, message=None):
    """Ana menüyü gösterir - menünün sabit kalması için aynı mesajı düzenler"""
    user_id = update.effective_user.id
    text = message if message else 'Hoş geldiniz! Lütfen bir seçenek seçin:'
    reply_markup = get_main_menu_keyboard(user_id)
    
    # Always use show_generic_menu for consistent behavior
    await show_generic_menu(
        update=update,
        context=context,
        text=text,
        reply_markup=reply_markup
    )
async def verify_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Şifre doğrulama işlemi"""
    user_id = update.effective_user.id
    user_password = update.message.text
    
    # Şifreyi gizle
    try:
        await update.message.delete()
    except Exception as e:
        logger.error(f"Error deleting password message: {e}")
    
    # Şifreyi kontrol et
    if user_password == BOT_PASSWORD:
        # Şifre doğru - kullanıcıyı yetkilendir
        try:
            # Önce kullanıcı kaydını kontrol et/oluştur
            db.cur.execute("SELECT telegram_id FROM users WHERE telegram_id = ?", (user_id,))
            if not db.cur.fetchone():
                db.cur.execute(
                    "INSERT INTO users (telegram_id, failed_payments, is_banned, authorized) VALUES (?, 0, 0, 1)",
                    (user_id,)
                )
            else:
                # Kullanıcı zaten var, sadece yetkilendir
                db.cur.execute(
                    "UPDATE users SET authorized = 1 WHERE telegram_id = ?",
                    (user_id,)
                )
            db.conn.commit()
            logger.info(f"User {user_id} authorized successfully")
        except Exception as e:
            logger.error(f"Error authorizing user {user_id}: {e}")
        
        # Şifre mesajını sil veya düzenle
        password_message_id = context.user_data.get('password_message_id')
        if password_message_id:
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=password_message_id
                )
            except Exception as e:
                logger.error(f"Error deleting password message: {e}")
        
        # Ana menüyü göster
        user_first_name = update.effective_user.first_name if update.effective_user.first_name else "Değerli Müşterimiz"
        welcome_message = WELCOME_MESSAGE_TEMPLATE.format(user_first_name)
        
        await show_main_menu(update, context, welcome_message)
        return ConversationHandler.END
    else:
        # Şifre yanlış - önceki mesajı tamamen sil
        password_message_id = context.user_data.get('password_message_id')
        if password_message_id:
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=password_message_id
                )
            except Exception as e:
                logger.debug(f"Could not delete previous password message: {e}")
        
        # Yeni bir mesaj gönder, herhangi bir menü butonu OLMADAN
        sent_message = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Yanlış şifre. Lütfen doğru şifreyi yazın:",
            reply_markup=None  # No buttons at all for wrong password
        )
        context.user_data['password_message_id'] = sent_message.message_id
        return PASSWORD_VERIFICATION
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Karşılama mesajını göster ve ana menüyü oluştur"""
    try:
        if context.args and len(context.args) > 0 and 'save_score_' in context.args[0]:
            try:
                # Parse score data using rsplit to handle session IDs with underscores
                parts = context.args[0].split('save_score_')[1].rsplit('_', 1)
                if len(parts) == 2:
                    game_session = parts[0]
                    score = int(parts[1])
                    user_id = update.effective_user.id
                    
                    logger.info(f"Processing game score: session={game_session}, score={score}, user={user_id}")
                    
                    # Save score to database
                    if db.save_game_score(user_id, game_session, score):
                        # Determine discount based on score
                        discount = 0
                        if score >= 2000:
                            discount = 15
                        elif score >= 1000:
                            discount = 10
                        elif score >= 500:
                            discount = 5
                            
                        if discount > 0:
                            # Create coupon
                            coupon_code = db.create_discount_coupon(user_id, discount, f"Flappy Weed {score} puan")
                            
                            await context.bot.send_message(
                                chat_id=user_id,
                                text=f"🎉 Tebrikler! {score} puan kazandınız ve %{discount} indirim kuponu elde ettiniz!\n\n"
                                     f"🏷️ Kupon kodu: {coupon_code}\n"
                                     f"Bir sonraki alışverişinizde bu kodu kullanabilirsiniz.",
                                reply_markup=InlineKeyboardMarkup([
                                    [InlineKeyboardButton("🎮 Tekrar Oyna", callback_data='play_flappy_weed')],
                                    [InlineKeyboardButton("🛍️ Alışverişe Başla", callback_data='products_menu')],
                                    [InlineKeyboardButton("🏆 Skor Tablosu", callback_data='show_leaderboard')]
                                ])
                            )
                        else:
                            await context.bot.send_message(
                                chat_id=user_id,
                                text=f"👏 Oyun tamamlandı! Skorunuz: {score}\n\n"
                                     f"💡 İpucu: 500 puan ve üzeri skorlarda indirim kuponları kazanabilirsiniz!",
                                reply_markup=InlineKeyboardMarkup([
                                    [InlineKeyboardButton("🎮 Tekrar Oyna", callback_data='play_flappy_weed')],
                                    [InlineKeyboardButton("🏆 Skor Tablosu", callback_data='show_leaderboard')],
                                    [InlineKeyboardButton("🔙 Oyun Menüsü", callback_data='games_menu')]
                                ])
                            )
                            
                        # Return early since we've handled the score already
                        return ConversationHandler.END
            except Exception as e:
                logger.error(f"Error processing game score in start command: {e}")
                # Continue to regular start flow if there was an error
        
        # Regular start command flow
        user_first_name = update.effective_user.first_name if update.effective_user.first_name else "Değerli Müşterimiz"
        user_id = update.effective_user.id
        
        # Admin kullanıcısını her zaman yetkili olarak işaretleyin
        if user_id == ADMIN_ID:
            try:
                # Doğrudan SQL sorgusu kullanarak admin kullanıcısını yetkili olarak ekle
                db.cur.execute("SELECT telegram_id FROM users WHERE telegram_id = ?", (user_id,))
                if not db.cur.fetchone():
                    db.cur.execute(
                        "INSERT INTO users (telegram_id, failed_payments, is_banned, authorized) VALUES (?, 0, 0, 1)",
                        (user_id,)
                    )
                else:
                    # Admin kullanıcısını yetkilendir
                    db.cur.execute(
                        "UPDATE users SET authorized = 1 WHERE telegram_id = ?",
                        (user_id,)
                    )
                db.conn.commit()
                logger.info(f"Admin user {user_id} set as authorized")
            except Exception as e:
                logger.error(f"Error setting admin authorization: {e}")
                
            # Admin için doğrudan ana menüyü göster
            welcome_message = WELCOME_MESSAGE_TEMPLATE.format(user_first_name)
            await show_main_menu(update, context, welcome_message)
            return ConversationHandler.END
        
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
        
        # Kullanıcı yetkilendirilmiş mi kontrol et
        if not db.is_user_authorized(user_id):
            sent_message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"🔐 Hoş geldiniz {user_first_name}!\n\nBu özel servis sadece yetkili kişiler içindir. Lütfen erişim şifresini girin:",
                reply_markup=None
            )
            # Mesaj ID'sini sakla
            context.user_data['password_message_id'] = sent_message.message_id
            return PASSWORD_VERIFICATION
        
        logger.info("Starting new conversation")
        # Kullanıcıyı veritabanına ekle
        logger.info(f"Adding user {user_id} to database")
        try:
            # Doğrudan SQL sorgusu kullanarak kullanıcıyı ekleyelim
            db.cur.execute("SELECT telegram_id FROM users WHERE telegram_id = ?", (user_id,))
            if not db.cur.fetchone():
                db.cur.execute(
                    "INSERT INTO users (telegram_id, failed_payments, is_banned, authorized) VALUES (?, 0, 0, 1)",
                    (user_id,)
                )
                db.conn.commit()
                logger.info(f"Successfully added user {user_id}")
        except Exception as e:
            logger.error(f"Error adding user {user_id}: {e}")
        
        user_first_name = update.effective_user.first_name if update.effective_user.first_name else "Değerli Müşterimiz"
        welcome_message = WELCOME_MESSAGE_TEMPLATE.format(user_first_name)
        
        await show_main_menu(update, context, welcome_message)
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        # Hata durumunda basit bir mesaj göster
        await show_generic_menu(
            update=update,
            context=context,
            text="Hoş geldiniz! Lütfen bir seçenek seçin:",
            reply_markup=get_main_menu_keyboard(update.effective_user.id)
        )
        logger.error(f"Fallback message sent for user {user_id}")
        return ConversationHandler.END