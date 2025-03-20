import uuid
import logging
import json
import asyncio
import random
import calendar
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import Database
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
db = Database('shop.db')

# Test için daha düşük puan eşikleri kullanacağız
REWARD_THRESHOLDS = {
    10: 5,   # 10 puan = %5 indirim
    20: 10,  # 20 puan = %10 indirim
    30: 15,  # 30 puan = %15 indirim
    40: 20,  # 40 puan = %20 indirim 
    50: 25   # 50 puan = %25 indirim
}

async def show_games_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the games menu with all available games"""
    try:
        # Clean up previous messages for cleaner UI
        if update.callback_query:
            try:
                await update.callback_query.message.delete()
            except Exception as e:
                logger.error(f"Error deleting message: {e}")
        
        user_id = update.effective_user.id
        
        # Get Flappy Weed stats
        user_best = db.get_user_best_score(user_id)
        user_total = db.get_user_total_score(user_id)
        
        # Get total games played
        db.cur.execute(
            "SELECT COUNT(*) FROM game_scores WHERE user_id = ?",
            (user_id,)
        )
        result = db.cur.fetchone()
        games_played = result[0] if result else 0
        
        # Calculate next month's reset date
        next_reset = get_next_month_reset_date()
        days_remaining = (next_reset - datetime.now()).days + 1
        
        # Check claimed discounts
        claimed_discounts = []
        for discount in sorted([REWARD_THRESHOLDS[threshold] for threshold in REWARD_THRESHOLDS]):
            if db.has_claimed_discount(user_id, discount):
                claimed_discounts.append(discount)
        
        # Create menu buttons
        keyboard = [
            [InlineKeyboardButton("🍀 Flappy Weed Oyna", callback_data='play_flappy_weed')],
            [InlineKeyboardButton("🎁 Ödüllerimi Talep Et", callback_data='claim_rewards')],
            [InlineKeyboardButton("🏆 Skor Tablosu", callback_data='show_leaderboard')],
            [InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]
        ]
        
        message = f"""🎮 Oyun Menüsü

🎲 Mevcut Oyunlar:

🍀 Flappy Weed:
- Yüksek puan yap ve ödül kazan
- En yüksek skorunuz: {user_best}
- Toplam puanınız: {user_total}

📊 İstatistikleriniz:
- 🎮 Toplam oynanan oyun: {games_played}
- 🥇 En yüksek skorunuz: {user_best}

⚠️ Puanlar ve skorlar ayın sonunda sıfırlanacak
⏳ Kalan süre: {days_remaining} gün"""

        if claimed_discounts:
            message += "\n\n📝 Bu ay talep ettiğiniz indirimler:"
            for discount in claimed_discounts:
                message += f"\n• %{discount} İndirim"
        
        # Add next reward info
        for threshold in sorted(REWARD_THRESHOLDS.keys()):
            if user_total < threshold:
                message += f"\n\n⭐ Sonraki ödül için {threshold - user_total} puan daha kazanmalısınız!"
                break
        
        # Send menu message
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing games menu: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Oyun menüsü gösterilirken bir hata oluştu.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )

# The rest of the file remains the same...
def get_next_month_reset_date():
    """Mevcut ayın son gününü hesapla (sıfırlama tarihi)"""
    now = datetime.now()
    
    # Bu ayın son gününü hesapla
    last_day = calendar.monthrange(now.year, now.month)[1]
    
    # Ayın son günü 23:59:59
    reset_date = datetime(now.year, now.month, last_day, 23, 59, 59)
    
    # Eğer bugün ayın son günüyse, bir sonraki ayın son gününü hesapla
    if now.day == last_day:
        if now.month == 12:
            next_year = now.year + 1
            next_month = 1
        else:
            next_year = now.year
            next_month = now.month + 1
            
        next_last_day = calendar.monthrange(next_year, next_month)[1]
        reset_date = datetime(next_year, next_month, next_last_day, 23, 59, 59)
    
    return reset_date

async def claim_rewards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcının puanlarına göre ödüllerini talep etmesini sağla - her indirim tier'ı ayda bir kez alınabilir"""
    user_id = update.effective_user.id
    
    try:
        # Kullanıcının toplam puanını al
        total_score = db.get_user_total_score(user_id)
        
        # Kullanıcının alabileceği ödülleri belirle
        available_rewards = []
        already_claimed = []
        
        for threshold, discount in sorted(REWARD_THRESHOLDS.items()):
            if total_score >= threshold:
                # Kullanıcı bu ay bu indirimi zaten aldı mı kontrol et
                if db.has_claimed_discount(user_id, discount):
                    already_claimed.append({
                        'threshold': threshold,
                        'discount': discount
                    })
                else:
                    available_rewards.append({
                        'threshold': threshold,
                        'discount': discount
                    })
        
        if not available_rewards and not already_claimed:
            # Kullanıcı hiçbir ödül hak etmemiş
            await update.callback_query.message.edit_text(
                text=f"""🎁 Ödül Talebi

❌ Henüz ödül alabilecek puanınız bulunmuyor.

💰 Mevcut puanınız: {total_score}
🎯 İlk ödül için gereken puan: {min(REWARD_THRESHOLDS.keys())}

🎮 Daha fazla puan kazanmak için oyun oynayın!""",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎮 Oyun Oyna", callback_data='play_flappy_weed')],
                    [InlineKeyboardButton("🔙 Oyun Menüsü", callback_data='games_menu')]
                ])
            )
            return
        
        message = f"""🎁 Ödül Talebi

💰 Mevcut puanınız: {total_score}
"""

        if available_rewards:
            # En yüksek kullanılabilir ödülü seç
            best_reward = available_rewards[-1]
            
            message += f"""
✅ Talep edebileceğiniz ödül:

💯 %{best_reward['discount']} İndirim Kuponu
📊 Gerekli puan: {best_reward['threshold']}

⚠️ Bu ödülü talep ederseniz, {best_reward['threshold']} puanınız kullanılacaktır.
📝 Kalan puanlarınız: {total_score - best_reward['threshold']} olacaktır.

⚠️ NOT: Her indirim oranını ayda sadece bir kez talep edebilirsiniz.

Ödülünüzü şimdi talep etmek istiyor musunuz?"""
            
            # Onay butonları
            keyboard = [
                [InlineKeyboardButton("✅ Ödülü Talep Et", callback_data=f"confirm_reward_{best_reward['threshold']}_{best_reward['discount']}")],
                [InlineKeyboardButton("❌ Vazgeç", callback_data='games_menu')]
            ]
        else:
            message += """
❌ Bu ay talep edebileceğiniz yeni ödül bulunmuyor!

⚠️ Her indirim oranını ayda sadece bir kez talep edebilirsiniz.

Bu ay zaten talep ettiğiniz indirimler:
"""
            for claimed in already_claimed:
                message += f"• %{claimed['discount']} ({claimed['threshold']} puan)\n"
                
            message += "\n📅 Yeni ay başlangıcında tekrar talep edebilirsiniz."
            
            keyboard = [
                [InlineKeyboardButton("🎮 Oyun Oyna", callback_data='play_flappy_weed')],
                [InlineKeyboardButton("🔙 Oyun Menüsü", callback_data='games_menu')]
            ]
        
        await update.callback_query.message.edit_text(
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    except Exception as e:
        logger.error(f"Ödül talebi işlenirken hata: {e}")
        await update.callback_query.message.edit_text(
            text="❌ Ödül talebi işlenirken bir hata oluştu.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Oyun Menüsü", callback_data='games_menu')
            ]])
        )
async def confirm_reward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ödül talebini onayla ve kuponu oluştur"""
    user_id = update.effective_user.id
    
    try:
        # Callback verisinden ödül bilgilerini çıkart
        data_parts = update.callback_query.data.split('_')
        threshold = int(data_parts[2])
        discount = int(data_parts[3])
        
        # Kullanıcının toplam puanını al
        total_score = db.get_user_total_score(user_id)
        
        # Puanın yeterli olduğundan emin ol
        if total_score < threshold:
            await update.callback_query.message.edit_text(
                text="❌ Yeterli puanınız bulunmuyor. Lütfen daha fazla oyun oynayın.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Oyun Menüsü", callback_data='games_menu')
                ]])
            )
            return
        
        # Bu indirim oranını bu ay zaten talep etmiş mi kontrol et
        if db.has_claimed_discount(user_id, discount):
            await update.callback_query.message.edit_text(
                text=f"❌ %{discount} indirim kuponunu bu ay zaten talep ettiniz. Her indirim oranını ayda bir kez talep edebilirsiniz.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Oyun Menüsü", callback_data='games_menu')
                ]])
            )
            return
        
        # Kuponu oluştur
        coupon_code = db.create_discount_coupon(user_id, discount, "Oyun Ödülü")
        
        if not coupon_code or coupon_code == "ERROR":
            # Kupon oluşturulamadı
            await update.callback_query.message.edit_text(
                text="❌ Kupon oluşturulurken bir hata oluştu. Lütfen daha sonra tekrar deneyin.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Oyun Menüsü", callback_data='games_menu')
                ]])
            )
            return
        
        # Kullanıcının bu ay bu indirim oranını talep ettiğini kaydet
        db.record_claimed_discount(user_id, discount)
        
        # Kullanılan puanı düş
        # Puanı azaltmak için negatif skor kaydet
        try:
            # Özel bir "puan düşürme" kaydı ekle
            db.cur.execute(
                "INSERT INTO game_scores (user_id, session_id, score, game_type) VALUES (?, ?, ?, ?)",
                (user_id, "reward_claim", -threshold, "reward_claim")
            )
            db.conn.commit()
            logger.info(f"Kullanıcı {user_id} ödül için {threshold} puan kullandı")
        except Exception as e:
            logger.error(f"Puan düşürülürken hata: {e}")
            # Hata olsa bile devam et, en azından kuponu oluşturduysak kullanıcı görsün
        
        # Kullanıcıya başarı mesajı göster
        message = f"""🎉 Tebrikler! Ödülünüz başarıyla oluşturuldu!

🎟️ Kupon Kodu: {coupon_code}
💯 İndirim Oranı: %{discount}
📆 Geçerlilik: 30 gün

📊 Kullanılan Puan: {threshold}
💰 Kalan Puanınız: {total_score - threshold}

⚠️ Not: Her indirim oranını ayda sadece bir kez talep edebilirsiniz.

Bu kuponu alışverişinizde kullanabilirsiniz. Kuponlarınızı "Kuponlarım" menüsünden görebilirsiniz."""
        
        await update.callback_query.message.edit_text(
            text=message,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛍️ Alışverişe Başla", callback_data='products_menu')],
                [InlineKeyboardButton("🎮 Daha Fazla Oyna", callback_data='play_flappy_weed')],
                [InlineKeyboardButton("🔙 Oyun Menüsü", callback_data='games_menu')]
            ])
        )
        
    except Exception as e:
        logger.error(f"Ödül onaylanırken hata: {e}")
        await update.callback_query.message.edit_text(
            text="❌ Ödül işlenirken bir hata oluştu.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Oyun Menüsü", callback_data='games_menu')
            ]])
        )
async def reset_monthly_scores():
    """Aylık skorları sıfırla ve talep edilen indirimleri resetle"""
    try:
        logger.info("Aylık skor sıfırlama işlemi başlatılıyor...")
        
        try:
            db.cur.execute("SELECT DISTINCT user_id FROM game_scores")
            users = [row[0] for row in db.cur.fetchall()]
            
            db.cur.execute("""
                CREATE TABLE IF NOT EXISTS game_scores_history (
                    month TEXT,
                    user_id INTEGER,
                    total_score INTEGER,
                    best_score INTEGER,
                    games_played INTEGER
                )
            """)
            
            current_month = datetime.now().strftime('%Y-%m')
            for user_id in users:
                db.cur.execute("""
                    INSERT INTO game_scores_history (month, user_id, total_score, best_score, games_played)
                    SELECT 
                        ?, 
                        ?, 
                        SUM(score), 
                        MAX(score), 
                        COUNT(*)
                    FROM game_scores 
                    WHERE user_id = ?
                """, (current_month, user_id, user_id))
        except Exception as e:
            logger.error(f"Skor geçmişi kaydedilirken hata: {e}")
        db.cur.execute("DELETE FROM game_scores")
        db.reset_claimed_discounts()
        db.conn.commit()
        logger.info("Tüm oyun skorları ve talep edilen indirimler başarıyla sıfırlandı.")
        return True
    except Exception as e:
        logger.error(f"Aylık skorları sıfırlarken hata: {e}")
        return False

async def schedule_monthly_reset(bot):
    """Aylık sıfırlama zamanlayıcısını başlat"""
    try:
        while True:
            try:
                # Sıfırlama tarihini hesapla (mevcut ayın son günü)
                next_reset = get_next_month_reset_date()
                
                # Şu anki tarih ile aradaki farkı hesapla
                now = datetime.now()
                time_delta = next_reset - now
                
                is_last_day_of_month = now.day == calendar.monthrange(now.year, now.month)[1]
                hours_left_today = 24 - now.hour
                
                logger.info(f"Bir sonraki sıfırlama: {next_reset.strftime('%Y-%m-%d %H:%M:%S')} "
                          f"({time_delta.days} gün, {time_delta.seconds // 3600} saat sonra)")
                
                if time_delta.days <= 2 and time_delta.days > 1:
                    await send_reset_notifications(bot)
                
                if is_last_day_of_month and hours_left_today <= 1:
                    if time_delta.total_seconds() <= 600:  # 10 dakika = 600 saniye
                        logger.info("Aylık sıfırlama zamanı geldi, işlem başlatılıyor...")
                        await reset_monthly_scores()
                        
                        await asyncio.sleep(3600)
                    else:
                        await asyncio.sleep(900)
                else:
                    await asyncio.sleep(3600)
                    
            except asyncio.CancelledError:
                logger.info("Sıfırlama zamanlayıcısı iptal edildi")
                return  # Görev iptal edildiğinde temiz çıkış
            except Exception as e:
                logger.error(f"Sıfırlama zamanlayıcısında hata: {e}")
                try:
                    await asyncio.sleep(3600)
                except asyncio.CancelledError:
                    logger.info("Sıfırlama zamanlayıcısı uyku sırasında iptal edildi")
                    return  # Uyku sırasında iptal edilirse temiz çıkış
    except asyncio.CancelledError:
        logger.info("Monthly reset scheduler task cancelled")
        return
    except Exception as e:
        logger.error(f"Unexpected error in schedule_monthly_reset: {e}")
    finally:
        logger.info("Monthly reset scheduler task completed")


async def send_reset_notifications(bot):
    """Tüm aktif kullanıcılara sıfırlama bildirimi gönder"""
    try:
        db.cur.execute("""
            SELECT DISTINCT user_id 
            FROM game_scores 
            WHERE created_at >= datetime('now', '-30 days')
        """)
        
        active_users = [row[0] for row in db.cur.fetchall()]
        logger.info(f"{len(active_users)} aktif kullanıcıya sıfırlama bildirimi gönderiliyor...")
        
        # Bildirim mesajı
        message = """⚠️ UYARI: AYLIK SIFIRLAMA YAKLAŞIYOR

🗓️ Tüm oyun puanları ve skorlar 2 gün sonra sıfırlanacak!

🎁 Kazandığınız puanlarla ödül almak için son şansınız!
1. Oyun menüsüne gidin
2. "Ödüllerimi Talep Et" butonuna tıklayın
3. Hak ettiğiniz indirimi alın

💯 Ödüllerinizi talep etmezseniz, tüm puanlarınız kaybolacak!"""
        
        # Tüm aktif kullanıcılara bildirim gönder
        for user_id in active_users:
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=message,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🎮 Oyun Menüsüne Git", callback_data='games_menu')],
                        [InlineKeyboardButton("🎁 Ödüllerimi Talep Et", callback_data='claim_rewards')]
                    ])
                )
            except Exception as e:
                logger.error(f"Kullanıcı {user_id}'e bildirim gönderilirken hata: {e}")
                continue
        
        logger.info("Sıfırlama bildirimleri gönderildi.")
        return True
    
    except Exception as e:
        logger.error(f"Sıfırlama bildirimleri gönderilirken hata: {e}")
        return False

async def play_flappy_weed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Flappy Weed oyununu başlat (oyun kısıtlamaları olmadan)"""
    user_id = update.effective_user.id
    
    try:
        # Oyun oturumu oluştur
        game_session = f"{user_id}_{str(uuid.uuid4())}"
        game_url = f"https://mmeekh.github.io/dened/Static/game.html?session={game_session}"
        
        # Oturumu veritabanına kaydet
        db.create_game_session(user_id, game_session)
        
        logger.info(f"Kullanıcı {user_id} oyunu başlatıyor, oturum: {game_session}")
        
        # Kullanıcı istatistiklerini al
        user_best = db.get_user_best_score(user_id)
        user_total = db.get_user_total_score(user_id)
        
        # Sonraki sıfırlama bilgisini hesapla
        next_reset = get_next_month_reset_date()
        days_remaining = (next_reset - datetime.now()).days + 1
        
        # Oyun talimatlarını ve başlat butonunu göster
        await update.callback_query.message.edit_text(
            text=f"""🍀 Flappy Weed Oyunu

🏆 En yüksek skorunuz: {user_best}
💰 Toplam puanınız: {user_total}
⏳ Aylık sıfırlamaya: {days_remaining} gün

Nasıl Oynanır:
• Ekrana tıklayarak weed parçasını zıplat
• Borulardan kaçın ve mümkün olduğunca ilerle
• Her bir borudan geçiş 1 puan kazandırır

🔊 Ses efektleri için telefonunuzun sesini açın!""",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ Oyunu Başlat", web_app={"url": game_url})],
                [InlineKeyboardButton("🔙 Oyun Menüsü", callback_data='games_menu')]
            ])
        )
    except Exception as e:
        logger.error(f"Oyun başlatılırken hata: {e}")
        await update.callback_query.message.edit_text(
            text="❌ Oyun başlatılırken bir hata oluştu.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Oyun Menüsü", callback_data='games_menu')
            ]])
        )

# Geriye dönük uyumluluk için start_flappy_game fonksiyonu eklendi
async def start_flappy_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Geriye dönük uyumluluk için - Flappy Weed oyunu başlatma fonksiyonu"""
    try:
        user_id = update.effective_user.id
        game_session = update.callback_query.data.split('_')[2]
        
        # Oturum bilgisini veritabanına kaydet
        db.create_game_session(user_id, game_session)
        
        game_url = f"https://mmeekh.github.io/dened/Static/game.html?session={game_session}"
        
        logger.info(f"User {user_id} started game with session {game_session}")
        
        # Web uygulamasını aç
        await update.callback_query.message.edit_text(
            text="🎮 Flappy Weed oyunu yükleniyor...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ Oyunu Oyna", web_app={"url": game_url})],
                [InlineKeyboardButton("🔙 Oyun Menüsü", callback_data='games_menu')]
            ])
        )
        
    except Exception as e:
        logger.error(f"Oyun başlatılırken hata: {e}")
        await update.callback_query.message.edit_text(
            text="❌ Oyun yüklenirken bir hata oluştu.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Oyun Menüsü", callback_data='games_menu')
            ]])
        )

async def handle_game_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Oyun skorunu kaydet ve ödül bilgisi göster"""
    try:
        user_id = update.effective_user.id
        game_session = None
        score = 0
        
        # Skor verilerini farklı formatlardan çıkart
        if update.message and update.message.text and 'save_score_' in update.message.text:
            parts = update.message.text.split('save_score_')[1].split('_')
            if len(parts) >= 2:
                game_session = parts[0]
                score = int(parts[1])
        else:
            # Diğer durumlar için varsayılan işleyici
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ Skor verisi alınamadı.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎮 Tekrar Oyna", callback_data='play_flappy_weed')],
                    [InlineKeyboardButton("🔙 Oyun Menüsü", callback_data='games_menu')]
                ])
            )
            return
        
        logger.info(f"Skor işleniyor: kullanıcı={user_id}, skor={score}")
        
        # Skoru normal tabloya kaydet
        db.cur.execute(
            "INSERT INTO game_scores (user_id, session_id, score) VALUES (?, ?, ?)",
            (user_id, game_session, score)
        )
        db.conn.commit()
        
        # Toplam skoru al
        db.cur.execute(
            "SELECT SUM(score) FROM game_scores WHERE user_id = ?",
            (user_id,)
        )
        result = db.cur.fetchone()
        total_score = result[0] if result and result[0] else 0
        
        # En yüksek skoru al
        user_best = db.get_user_best_score(user_id)
        
        # Bu skorla elde edilebilecek potansiyel ödülü hesapla
        potential_reward = None
        for threshold in sorted(REWARD_THRESHOLDS.keys()):
            if total_score >= threshold:
                potential_reward = {
                    'threshold': threshold,
                    'discount': REWARD_THRESHOLDS[threshold]
                }
        
        # Tamamlama mesajını göster
        message = f"""👏 Oyun tamamlandı! {score} puan kazandınız!

🥇 En yüksek skorunuz: {user_best}
💰 Toplam Puanınız: {total_score}"""

        # Ödül bilgisi ekle
        if potential_reward:
            message += f"\n\n🎁 Şu anda %{potential_reward['discount']} indirim kuponuna hak kazandınız!"
            message += "\n💡 Ödülünüzü almak için 'Ödüllerimi Talep Et' butonunu kullanın."
        else:
            # Sonraki ödüle ne kadar kaldığını göster
            next_threshold = min([t for t in REWARD_THRESHOLDS.keys() if t > total_score], default=None)
            if next_threshold:
                message += f"\n\n💡 %{REWARD_THRESHOLDS[next_threshold]} indirim için {next_threshold - total_score} puana daha ihtiyacınız var."
        
        # Sonraki sıfırlama bilgisini ekle
        next_reset = get_next_month_reset_date()
        days_remaining = (next_reset - datetime.now()).days + 1
        message += f"\n\n⚠️ Puanlarınız {days_remaining} gün sonra sıfırlanacak."
        
        await context.bot.send_message(
            chat_id=user_id,
            text=message,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎮 Tekrar Oyna", callback_data='play_flappy_weed')],
                [InlineKeyboardButton("🎁 Ödüllerimi Talep Et", callback_data='claim_rewards')],
                [InlineKeyboardButton("🔙 Oyun Menüsü", callback_data='games_menu')]
            ])
        )
        
    except Exception as e:
        logger.error(f"Skor işlenirken hata: {e}", exc_info=True)
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ Skor işlenirken bir hata oluştu.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎮 Tekrar Oyna", callback_data='play_flappy_weed')],
                    [InlineKeyboardButton("🔙 Oyun Menüsü", callback_data='games_menu')]
                ])
            )
        except:
            pass

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skor tablosunu göster"""
    try:
        # En yüksek 10 skoru getir
        scores = db.get_top_scores(10)
        user_id = update.effective_user.id
        
        # Kullanıcının kendi en yüksek skoru ve toplam skoru
        user_best = db.get_user_best_score(user_id)
        user_total = db.get_user_total_score(user_id)
        
        if not scores:
            message = "🏆 Skor Tablosu\n\nHenüz kimse oyun oynamamış. İlk skor senin olabilir!"
        else:
            message = "🏆 Flappy Weed Skor Tablosu - En Yüksek Skorlar\n\n"
            
            for i, score_data in enumerate(scores):
                score_user_id = score_data[0]
                score = score_data[1]
                
                medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"{i+1}."
                display_name = f"Kullanıcı {score_user_id}"
                is_you = " (Sen)" if score_user_id == user_id else ""
                
                message += f"{medal} {display_name}{is_you}: {score} puan\n"
            
            # Kullanıcı ilk 10'da değilse kendi bilgilerini ekle
            if user_id not in [uid for uid, _, *_ in scores]:
                message += f"\n🎮 Senin en yüksek skorun: {user_best} puan"
            
            message += f"\n\n💰 Toplam Puanın: {user_total}"
            
            # Potansiyel ödül bilgisini ekle
            potential_reward = None
            for threshold in sorted(REWARD_THRESHOLDS.keys()):
                if user_total >= threshold:
                    potential_reward = {
                        'threshold': threshold,
                        'discount': REWARD_THRESHOLDS[threshold]
                    }
            
            if potential_reward:
                message += f"\n\n🎁 Şu anda %{potential_reward['discount']} indirim kuponuna hak kazandınız!"
            else:
                # Sonraki ödüle ne kadar kaldığını göster
                next_threshold = min([t for t in REWARD_THRESHOLDS.keys() if t > user_total], default=None)
                if next_threshold:
                    message += f"\n\n💡 %{REWARD_THRESHOLDS[next_threshold]} indirim için {next_threshold - user_total} puana daha ihtiyacınız var."
            
            # Sıfırlama bilgisini ekle
            next_reset = get_next_month_reset_date()
            days_remaining = (next_reset - datetime.now()).days + 1
            message += f"\n\n⚠️ Puanlarınız {days_remaining} gün sonra sıfırlanacak."
        
        await update.callback_query.message.edit_text(
            text=message,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎮 Oyna", callback_data='play_flappy_weed')],
                [InlineKeyboardButton("🎁 Ödüllerimi Talep Et", callback_data='claim_rewards')],
                [InlineKeyboardButton("🔙 Oyun Menüsü", callback_data='games_menu')]
            ])
        )
        
    except Exception as e:
        logger.error(f"Skor tablosu gösterilirken hata: {e}")
        await update.callback_query.message.edit_text(
            text="❌ Skor tablosu gösterilirken bir hata oluştu.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Oyun Menüsü", callback_data='games_menu')
            ]])
        )