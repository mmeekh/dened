import logging
import json
import uuid
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import Database
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
db = Database('shop.db')

async def show_games_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Oyun menüsünü göster"""
    try:
        # Son mesajı sil
        if update.callback_query:
            try:
                await update.callback_query.message.delete()
            except Exception as e:
                logger.error(f"Mesaj silinirken hata: {e}")
        
        user_id = update.effective_user.id
        
        # Kullanıcının günlük kalan oyun hakkını al
        remaining_games = db.get_remaining_daily_games(user_id)
        
        # Kullanıcının en yüksek skoru ve toplam puanını al
        user_best = db.get_user_best_score(user_id)
        user_total = db.get_user_total_score(user_id)
        
        # Menü butonlarını hazırla
        keyboard = [
            [InlineKeyboardButton("🍀 Flappy Weed Oyna", callback_data='play_flappy_weed')],
            [InlineKeyboardButton("🏆 Skor Tablosu", callback_data='show_leaderboard')],
            [InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]
        ]
        
        # Menü mesajını hazırla
        message = f"""🎮 Oyun Menüsü

🍀 Flappy Weed oyununda yüksek puan yap ve ödül kazan!

📊 İstatistikleriniz:
• 🎯 Günlük oyun hakkı: {remaining_games}/3
• 🥇 En yüksek skorunuz: {user_best}
• 💰 Toplam puanınız: {user_total}

🎁 ÖDÜL SİSTEMİ (Toplam Puana Göre):
• 200+ Puan = %5 İndirim
• 500+ Puan = %10 İndirim
• 1000+ Puan = %15 İndirim
• 1500+ Puan = %25 İndirim
• 2000+ Puan = Premium Ürün Hediyesi

🔄 Her oyunda kazandığınız puanlar toplanır ve ödüllere çevrilir!
📱 Oynamak için 'Flappy Weed Oyna' butonuna tıklayın."""
        
        if user_total < 200:
            message += f"\n\n⭐ Sonraki ödül için {200 - user_total} puan daha kazanmalısınız!"
        elif user_total < 500:
            message += f"\n\n⭐ Sonraki ödül için {500 - user_total} puan daha kazanmalısınız!"
        elif user_total < 1000:
            message += f"\n\n⭐ Sonraki ödül için {1000 - user_total} puan daha kazanmalısınız!"
        elif user_total < 1500:
            message += f"\n\n⭐ Sonraki ödül için {1500 - user_total} puan daha kazanmalısınız!"
        elif user_total < 2000:
            message += f"\n\n⭐ Sonraki ödül için {2000 - user_total} puan daha kazanmalısınız!"
        else:
            message += "\n\n🌟 Tebrikler! En yüksek ödül seviyesine ulaştınız!"
        
        # Mesajı gönder
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Oyun menüsü gösterilirken hata: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Oyun menüsü gösterilirken bir hata oluştu.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )
        
async def play_flappy_weed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Flappy Weed oyununu başlat"""
    user_id = update.effective_user.id
    
    try:
        # Oyun oturumu benzersiz bir şekilde oluştur - user_id'yi de dahil et
        game_session = f"{user_id}_{str(uuid.uuid4())}"
        
        # Doğrudan oyun URL'sini oluştur
        game_url = f"https://mmeekh.github.io/dened/Static/game.html?session={game_session}"
        
        # Oyun bilgilerini veritabanına kaydet - bu satır çok önemli!
        db.create_game_session(user_id, game_session)
        
        logger.info(f"User {user_id} started game with session {game_session}")
        
        # Oyun tanıtım mesajı ve doğrudan başlatma butonu göster
        await update.callback_query.message.edit_text(
            text=f"🍀 Flappy Weed Oyunu\n\n"
                 f"Nasıl Oynanır:\n"
                 f"- Ekrana tıklayarak weed parçasını zıplat\n"
                 f"- Borulardan kaçın ve mümkün olduğunca ilerle\n"
                 f"- Her bir borudan geçiş 1 puan kazandırır\n\n"
                 f"🔊 Ses efektleri için telefonunuzun sesini açın!",
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
async def start_flappy_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Geriye dönük uyumluluk için mevcut - oyunu başlatır"""
    try:
        user_id = update.effective_user.id
        game_session = update.callback_query.data.split('_')[2]
        
        # Oturum bilgisini veritabanına kaydet - bu satırı ekliyoruz!
        db.create_game_session(user_id, game_session)
        
        game_url = f"https://mmeekh.github.io/dened/Static/game.html?session={game_session}"
        
        logger.info(f"User {user_id} started game with session {game_session}")
        
        # Doğrudan web_app açılımına yönlendir
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
        
    except Exception as e:
        logger.error(f"Oyun başlatılırken hata: {e}")
        await update.callback_query.message.edit_text(
            text="❌ Oyun yüklenirken bir hata oluştu.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Oyun Menüsü", callback_data='games_menu')
            ]])
        )
async def handle_game_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Oyun skorunu kaydet ve toplam puana göre ödül kontrol et"""
    try:
        user_id = update.effective_user.id
        
        # WebApp veri alımıyla veya başlatma komutundan gelen veriyi işle
        if update.message and update.message.web_app_data:
            # WebApp'ten gelen veri
            data = json.loads(update.message.web_app_data.data)
            game_session = data.get('session')
            score = data.get('score', 0)
            logger.info(f"WebApp data: session={game_session}, score={score}")
        elif update.message and update.message.text and 'save_score_' in update.message.text:
            # URL'den gelen veri
            parts = update.message.text.split('save_score_')[1].split('_')
            game_session = parts[0]
            score = int(parts[1])
            logger.info(f"URL data: session={game_session}, score={score}, raw={update.message.text}")
        else:
            # Callback verisi
            try:
                data = json.loads(update.callback_query.data.replace('save_score_', ''))
                game_session = data.get('session')
                score = data.get('score', 0)
                logger.info(f"Callback data: session={game_session}, score={score}")
            except:
                # Düz metin olarak parse etmeyi dene
                parts = update.callback_query.data.split('save_score_')[1].split('_')
                game_session = parts[0]
                score = int(parts[1])
                logger.info(f"Callback text data: session={game_session}, score={score}")
                
        logger.info(f"Processing score {score} for session {game_session} by user {user_id}")
        
        # Oyun oturumunun gerçekten kullanıcıya ait olup olmadığını kontrol et
        if not db.validate_game_session(user_id, game_session):
            logger.warning(f"Invalid game session {game_session} for user {user_id}")
            await context.bot.send_message(
                chat_id=user_id,
                text="⚠️ Geçersiz oyun oturumu! Skor kaydedilemedi.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎮 Tekrar Oyna", callback_data='play_flappy_weed')],
                    [InlineKeyboardButton("🔙 Oyun Menüsü", callback_data='games_menu')]
                ])
            )
            return
            
        # Skoru veritabanına kaydet
        if db.save_game_score(user_id, game_session, score):
            logger.info(f"Score {score} saved successfully for user {user_id}")
            # Toplam skoru hesapla
            total_score = db.get_user_total_score(user_id)
            
            # Ödül seviyelerini kontrol et
            reward_level = check_reward_level(total_score)
            previous_level = context.user_data.get('reward_level', 0)
            
            # Yeni bir ödül seviyesine ulaşıldı mı kontrol et
            if reward_level > previous_level:
                context.user_data['reward_level'] = reward_level
                
                # Ödül seviyesine göre indirim kuponu oluştur
                discount = 0
                if reward_level == 5:
                    message = f"🎁 TEBRİKLER! Toplam {total_score} puana ulaştınız ve Premium Ürün kazandınız!"
                    discount = 100  # Özel işaretleme için
                elif reward_level == 4:
                    discount = 25
                elif reward_level == 3:
                    discount = 15
                elif reward_level == 2:
                    discount = 10
                elif reward_level == 1:
                    discount = 5
                    
                if discount > 0:
                    # Kupon oluştur
                    if discount == 100:
                        coupon_code = db.create_discount_coupon(user_id, 100, f"Premium Ürün Ödülü - {total_score} puan")
                        message += f"\n\n🏆 Hediye Kodu: {coupon_code}\nBu kodu Admin'e ileterek premium ürününüzü talep edebilirsiniz!"
                    else:
                        coupon_code = db.create_discount_coupon(user_id, discount, f"Toplam {total_score} puan ödülü")
                        message = f"🎉 Tebrikler! Toplam {total_score} puana ulaştınız ve %{discount} indirim kuponu kazandınız!\n\n🏷️ Kupon kodu: {coupon_code}"
                    
                    # Kupon kazanıldığında butonlara "Kuponlarım" butonu da ekleyelim
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=message,
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🎟️ Kuponlarımı Göster", callback_data='my_coupons')],
                            [InlineKeyboardButton("🎮 Tekrar Oyna", callback_data='play_flappy_weed')],
                            [InlineKeyboardButton("🛍️ Alışverişe Başla", callback_data='products_menu')],
                            [InlineKeyboardButton("🏆 Skor Tablosu", callback_data='show_leaderboard')]
                        ])
                    )
                    return
            
            # Bu oyunda yeni ödül seviyesine ulaşılmadıysa da skor yine de yüksekse daha küçük bir ödül verelim
            if score >= 500 and score < 1000:
                # Tek oyun skoru için küçük kupon verme (sadece nadiren)
                if random.randint(1, 5) == 1:  # %20 şans
                    coupon_code = db.create_discount_coupon(user_id, 5, f"Tek oyunda {score} puan özel ödülü")
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"🎁 Şanslı gün! Tek oyunda {score} puan kazandınız ve %5 indirim kuponu elde ettiniz!\n\n🏷️ Kupon kodu: {coupon_code}",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🎟️ Kuponlarımı Göster", callback_data='my_coupons')],
                            [InlineKeyboardButton("🎮 Tekrar Oyna", callback_data='play_flappy_weed')],
                            [InlineKeyboardButton("🛍️ Alışverişe Başla", callback_data='products_menu')]
                        ])
                    )
                    return
            elif score >= 1000:
                # Tek oyunda 1000+ puan her zaman kupon kazandırır
                discount = 10 if score >= 1500 else 7
                coupon_code = db.create_discount_coupon(user_id, discount, f"Tek oyunda {score} puan özel ödülü")
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"🏆 Mükemmel oyun! Tek seferde {score} puan kazandınız ve %{discount} özel indirim kuponu elde ettiniz!\n\n🏷️ Kupon kodu: {coupon_code}",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🎟️ Kuponlarımı Göster", callback_data='my_coupons')],
                        [InlineKeyboardButton("🎮 Tekrar Oyna", callback_data='play_flappy_weed')],
                        [InlineKeyboardButton("🛍️ Alışverişe Başla", callback_data='products_menu')]
                    ])
                )
                return
            
            # Normal oyun tamamlama mesajı gönder
            await context.bot.send_message(
                chat_id=user_id,
                text=f"👏 Oyun tamamlandı! Bu oyunda {score} puan kazandınız!\n\n"
                     f"💰 Toplam Biriken Puanınız: {total_score}\n\n"
                     f"💡 İpucu: Oynamaya devam ederek puanlarınızı toplayın ve özel ödüller kazanın!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎮 Tekrar Oyna", callback_data='play_flappy_weed')],
                    [InlineKeyboardButton("🏆 Skor Tablosu", callback_data='show_leaderboard')],
                    [InlineKeyboardButton("🔙 Oyun Menüsü", callback_data='games_menu')]
                ])
            )
        else:
            logger.error(f"Failed to save score {score} for user {user_id}")
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ Skor kaydedilirken bir hata oluştu.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎮 Tekrar Oyna", callback_data='play_flappy_weed')],
                    [InlineKeyboardButton("🔙 Oyun Menüsü", callback_data='games_menu')]
                ])
            )
                
    except Exception as e:
        logger.error(f"Skor kaydedilirken hata: {e}")
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ Bir hata oluştu. Lütfen tekrar deneyin.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎮 Tekrar Oyna", callback_data='play_flappy_weed')],
                    [InlineKeyboardButton("🔙 Oyun Menüsü", callback_data='games_menu')]
                ])
            )
        except:
            pass
        
def check_reward_level(total_score: int) -> int:
    """Toplam puana göre ödül seviyesini belirle
    Seviye 0: 0-199 puan
    Seviye 1: 200-499 puan
    Seviye 2: 500-999 puan
    Seviye 3: 1000-1499 puan
    Seviye 4: 1500-1999 puan
    Seviye 5: 2000+ puan
    """
    if total_score >= 2000:
        return 5
    elif total_score >= 1500:
        return 4
    elif total_score >= 1000:
        return 3
    elif total_score >= 500:
        return 2
    elif total_score >= 200:
        return 1
    else:
        return 0

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
            
            # Add user's statistics if not in top 10
            if user_id not in [uid for uid, _, *_ in scores]:
                message += f"\n🎮 Senin en yüksek skorun: {user_best} puan"
            
            message += f"\n\n💰 Toplam Biriken Puanın: {user_total}"
            
            # Add rewards information based on total score
            reward_info = get_reward_info(user_total)
            if reward_info:
                message += f"\n\n🎁 {reward_info}"
        
        await update.callback_query.message.edit_text(
            text=message,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎮 Oyna", callback_data='play_flappy_weed')],
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
        
def get_reward_info(total_score: int) -> str:
    """Get reward information based on total score"""
    if total_score >= 2000:
        return "2000+ Puan: Premium Ürün Hediyesi! 🎁"
    elif total_score >= 1500:
        return "1500+ Puan: %25 İndirim Kuponu 🏷️"
    elif total_score >= 1000:
        return "1000+ Puan: %15 İndirim Kuponu 🏷️"
    elif total_score >= 500:
        return "500+ Puan: %10 İndirim Kuponu 🏷️"
    elif total_score >= 200:
        return "200+ Puan: %5 İndirim Kuponu 🏷️"
    else:
        return f"Sonraki ödül için {200 - total_score} puan daha kazanmalısın"