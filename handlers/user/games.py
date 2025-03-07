import uuid
import logging
import json
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import Database
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
db = Database('shop.db')

async def show_games_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show game menu with updated chance limit"""
    try:
        # Delete previous message
        if update.callback_query:
            try:
                await update.callback_query.message.delete()
            except Exception as e:
                logger.error(f"Error deleting message: {e}")
        
        user_id = update.effective_user.id
        
        # Get user's daily remaining game chances
        remaining_games = db.get_remaining_daily_games(user_id)
        
        # Get user's stats
        user_best = db.get_user_best_score(user_id)
        user_total = db.get_user_total_score(user_id)
        
        # Prepare menu buttons
        keyboard = [
            [InlineKeyboardButton("🍀 Flappy Weed Oyna", callback_data='play_flappy_weed')],
            [InlineKeyboardButton("🏆 Skor Tablosu", callback_data='show_leaderboard')],
            [InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]
        ]
        
        # Menu message with updated chance limit
        message = f"""🎮 Oyun Menüsü

🍀 Flappy Weed oyununda yüksek puan yap ve ödül kazan!

📊 İstatistikleriniz:
• 🎯 Günlük oyun hakkı: {remaining_games}/5
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
        
        # Add next reward information
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
        
        # Send the message
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error showing game menu: {e}")
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
    """Handle game score saving and reward distribution"""
    try:
        user_id = update.effective_user.id
        game_session = None
        score = 0
        
        # Parse data from different sources
        if update.message and update.message.web_app_data:
            data = json.loads(update.message.web_app_data.data)
            game_session = data.get('session')
            score = int(data.get('score', 0))
        elif update.message and update.message.text and 'save_score_' in update.message.text:
            parts = update.message.text.split('save_score_')[1].rsplit('_', 1)
            if len(parts) == 2:
                game_session = parts[0]
                score = int(parts[1])
        elif update.callback_query and 'save_score_' in update.callback_query.data:
            parts = update.callback_query.data.split('save_score_')[1].rsplit('_', 1)
            if len(parts) == 2:
                game_session = parts[0]
                score = int(parts[1])
        
        if not game_session or score <= 0:
            logger.warning(f"Invalid game data: session={game_session}, score={score}")
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ Geçersiz oyun verisi. Skor kaydedilemedi.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎮 Tekrar Oyna", callback_data='play_flappy_weed')],
                    [InlineKeyboardButton("🔙 Oyun Menüsü", callback_data='games_menu')]
                ])
            )
            return
        
        logger.info(f"Processing score: user={user_id}, session={game_session}, score={score}")
        
        # MANUALLY UPDATE GAME CHANCES - Direct database approach
        try:
            db.conn.execute("BEGIN TRANSACTION")
            
            # Check current chances
            db.cur.execute(
                "SELECT daily_chances, last_reset FROM game_chances WHERE user_id = ?",
                (user_id,)
            )
            result = db.cur.fetchone()
            
            current_time = datetime.now()
            current_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
            
            if result:
                chances, last_reset_str = result
                # Parse last reset time safely
                try:
                    if isinstance(last_reset_str, str):
                        last_reset = datetime.strptime(last_reset_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
                    else:
                        last_reset = last_reset_str
                except:
                    last_reset = current_time - timedelta(days=1)  # Default to yesterday
                
                # Check if reset needed (new day)
                if (current_time - last_reset).days > 0:
                    logger.info(f"Resetting daily game chances for user {user_id}")
                    db.cur.execute(
                        "UPDATE game_chances SET daily_chances = 4, last_reset = ? WHERE user_id = ?",
                        (current_time_str, user_id)
                    )
                    remaining_chances = 4  # Already using 1 chance
                else:
                    # Not a new day, just decrement
                    if chances > 0:
                        db.cur.execute(
                            "UPDATE game_chances SET daily_chances = daily_chances - 1 WHERE user_id = ?",
                            (user_id,)
                        )
                        remaining_chances = chances - 1
                    else:
                        # No chances left
                        db.conn.execute("ROLLBACK")
                        await context.bot.send_message(
                            chat_id=user_id,
                            text="⚠️ Günlük oyun hakkınız kalmadı! Yarın tekrar deneyebilirsiniz.",
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton("🔙 Oyun Menüsü", callback_data='games_menu')]
                            ])
                        )
                        return
            else:
                # First time playing, create record with 4 chances left (using 1 now)
                db.cur.execute(
                    "INSERT INTO game_chances (user_id, daily_chances, last_reset) VALUES (?, 4, ?)",
                    (user_id, current_time_str)
                )
                remaining_chances = 4
            
            # Save the score
            db.cur.execute(
                "INSERT INTO game_scores (user_id, session_id, score) VALUES (?, ?, ?)",
                (user_id, game_session, score)
            )
            
            # Mark session as used
            db.cur.execute(
                "UPDATE game_sessions SET is_used = 1 WHERE user_id = ? AND session_id = ?",
                (user_id, game_session)
            )
            
            # Commit all changes
            db.conn.execute("COMMIT")
            logger.info(f"Score {score} saved for user {user_id}, remaining chances: {remaining_chances}")
            
        except Exception as db_error:
            logger.error(f"Database error: {db_error}")
            db.conn.execute("ROLLBACK")
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ Veritabanı hatası. Skor kaydedilemedi.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎮 Tekrar Oyna", callback_data='play_flappy_weed')],
                    [InlineKeyboardButton("🔙 Oyun Menüsü", callback_data='games_menu')]
                ])
            )
            return
        
        # Get updated total score
        db.cur.execute(
            "SELECT SUM(score) FROM game_scores WHERE user_id = ?",
            (user_id,)
        )
        result = db.cur.fetchone()
        total_score = result[0] if result and result[0] else 0
        
        # Check reward levels
        reward_level = check_reward_level(total_score)
        previous_level = context.user_data.get('reward_level', 0)
        
        # Handle level-up rewards
        if reward_level > previous_level:
            context.user_data['reward_level'] = reward_level
            
            # Determine reward
            discount = 0
            if reward_level == 5:  # 2000+ points
                message = f"🎁 TEBRİKLER! Toplam {total_score} puana ulaştınız ve Premium Ürün kazandınız!"
                discount = 100  # Special marking for premium product
            elif reward_level == 4:  # 1500+ points
                discount = 25
            elif reward_level == 3:  # 1000+ points
                discount = 15
            elif reward_level == 2:  # 500+ points
                discount = 10
            elif reward_level == 1:  # 200+ points
                discount = 5
                
            if discount > 0:
                # Create coupon
                if discount == 100:
                    coupon_code = db.create_discount_coupon(user_id, 100, f"Premium Ürün Ödülü - {total_score} puan")
                    message += f"\n\n🏆 Hediye Kodu: {coupon_code}\nBu kodu Admin'e ileterek premium ürününüzü talep edebilirsiniz!"
                else:
                    coupon_code = db.create_discount_coupon(user_id, discount, f"Toplam {total_score} puan ödülü")
                    message = f"🎉 Tebrikler! Toplam {total_score} puana ulaştınız ve %{discount} indirim kuponu kazandınız!\n\n🏷️ Kupon kodu: {coupon_code}"
                
                # Show message with coupon info
                await context.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🎟️ Kuponlarımı Göster", callback_data='my_coupons')],
                        [InlineKeyboardButton("🎮 Tekrar Oyna", callback_data='play_flappy_weed')],
                        [InlineKeyboardButton("🔙 Oyun Menüsü", callback_data='games_menu')]
                    ])
                )
                return
        
        # Check for single-game high score rewards
        if score >= 1000:
            # Always reward 1000+ points in a single game
            discount = 10 if score >= 1500 else 7
            coupon_code = db.create_discount_coupon(user_id, discount, f"Tek oyunda {score} puan özel ödülü")
            await context.bot.send_message(
                chat_id=user_id,
                text=f"🏆 Mükemmel oyun! Tek seferde {score} puan kazandınız ve %{discount} özel indirim kuponu elde ettiniz!\n\n"
                     f"🎟️ Kupon kodu: {coupon_code}\n"
                     f"Kalan Oyun Hakkı: {remaining_chances}/5",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎟️ Kuponlarımı Göster", callback_data='my_coupons')],
                    [InlineKeyboardButton("🎮 Tekrar Oyna", callback_data='play_flappy_weed')],
                    [InlineKeyboardButton("🔙 Oyun Menüsü", callback_data='games_menu')]
                ])
            )
            return
        elif score >= 500 and random.randint(1, 5) == 1:  # 20% chance
            coupon_code = db.create_discount_coupon(user_id, 5, f"Tek oyunda {score} puan özel ödülü")
            await context.bot.send_message(
                chat_id=user_id,
                text=f"🎁 Şanslı gün! Tek oyunda {score} puan kazandınız ve %5 indirim kuponu elde ettiniz!\n\n"
                     f"🎟️ Kupon kodu: {coupon_code}\n"
                     f"Kalan Oyun Hakkı: {remaining_chances}/5",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎟️ Kuponlarımı Göster", callback_data='my_coupons')],
                    [InlineKeyboardButton("🎮 Tekrar Oyna", callback_data='play_flappy_weed')],
                    [InlineKeyboardButton("🔙 Oyun Menüsü", callback_data='games_menu')]
                ])
            )
            return
        
        # Default completion message
        await context.bot.send_message(
            chat_id=user_id,
            text=f"👏 Oyun tamamlandı! Bu oyunda {score} puan kazandınız!\n\n"
                 f"💰 Toplam Biriken Puanınız: {total_score}\n"
                 f"🎮 Kalan Oyun Hakkı: {remaining_chances}/5\n\n"
                 f"💡 İpucu: Oynamaya devam ederek puanlarınızı toplayın ve özel ödüller kazanın!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎮 Tekrar Oyna", callback_data='play_flappy_weed')],
                [InlineKeyboardButton("🏆 Skor Tablosu", callback_data='show_leaderboard')],
                [InlineKeyboardButton("🔙 Oyun Menüsü", callback_data='games_menu')]
            ])
        )
    
    except Exception as e:
        logger.error(f"Error in handle_game_score: {e}", exc_info=True)
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