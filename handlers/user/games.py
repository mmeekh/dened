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
    """Show game menu without play limits"""
    try:
        # Delete previous message if possible
        if update.callback_query:
            try:
                await update.callback_query.message.delete()
            except Exception as e:
                logger.error(f"Error deleting message: {e}")
        
        user_id = update.effective_user.id
        
        # Get user stats
        user_best = db.get_user_best_score(user_id)
        user_total = db.get_user_total_score(user_id)
        
        # Get total games played
        db.cur.execute(
            "SELECT COUNT(*) FROM game_scores WHERE user_id = ?",
            (user_id,)
        )
        result = db.cur.fetchone()
        games_played = result[0] if result else 0
        
        # Prepare menu
        keyboard = [
            [InlineKeyboardButton("🍀 Flappy Weed Oyna", callback_data='play_flappy_weed')],
            [InlineKeyboardButton("🏆 Skor Tablosu", callback_data='show_leaderboard')],
            [InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]
        ]
        
        message = f"""🎮 Oyun Menüsü

🍀 Flappy Weed oyununda yüksek puan yap ve ödül kazan!

📊 İstatistikleriniz:
- 🎮 Toplam oynanan oyun: {games_played}
- 🥇 En yüksek skorunuz: {user_best}
- 💰 Toplam puanınız: {user_total}

🎁 ÖDÜL SİSTEMİ (Toplam Puana Göre):
- 200+ Puan = %5 İndirim
- 500+ Puan = %10 İndirim
- 1000+ Puan = %15 İndirim
- 1500+ Puan = %25 İndirim
- 2000+ Puan = Premium Ürün Hediyesi

🔄 Her oyunda kazandığınız puanlar toplanır ve ödüllere çevrilir!
📱 Oynamak için 'Flappy Weed Oyna' butonuna tıklayın."""
        
        # Add next reward info
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
        
        # Send menu
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
    """Start Flappy Weed game without play limits"""
    user_id = update.effective_user.id
    
    try:
        # Create a game session
        game_session = f"{user_id}_{str(uuid.uuid4())}"
        game_url = f"https://mmeekh.github.io/dened/Static/game.html?session={game_session}"
        
        # Save session to database
        db.create_game_session(user_id, game_session)
        
        logger.info(f"User {user_id} starting game with session {game_session}")
        
        # Get user stats
        user_best = db.get_user_best_score(user_id)
        user_total = db.get_user_total_score(user_id)
        
        # Show game instructions and start button
        await update.callback_query.message.edit_text(
            text=f"🍀 Flappy Weed Oyunu\n\n"
                 f"🏆 En yüksek skorunuz: {user_best}\n"
                 f"💰 Toplam puanınız: {user_total}\n\n"
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
    """Handle game score saving without play limits"""
    try:
        user_id = update.effective_user.id
        game_session = None
        score = 0
        
        # Extract score data from different formats
        if update.message and update.message.text and 'save_score_' in update.message.text:
            parts = update.message.text.split('save_score_')[1].split('_')
            if len(parts) >= 2:
                game_session = parts[0]
                score = int(parts[1])
        else:
            # Default handler for other cases
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ Skor verisi alınamadı.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎮 Tekrar Oyna", callback_data='play_flappy_weed')],
                    [InlineKeyboardButton("🔙 Oyun Menüsü", callback_data='games_menu')]
                ])
            )
            return
        
        logger.info(f"Processing score: user={user_id}, score={score}")
        
        # Save score to normal table
        db.cur.execute(
            "INSERT INTO game_scores (user_id, session_id, score) VALUES (?, ?, ?)",
            (user_id, game_session, score)
        )
        db.conn.commit()
        
        # Get total score
        db.cur.execute(
            "SELECT SUM(score) FROM game_scores WHERE user_id = ?",
            (user_id,)
        )
        result = db.cur.fetchone()
        total_score = result[0] if result and result[0] else 0
        
        # Get best score
        user_best = db.get_user_best_score(user_id)
        
        # Show completion message
        await context.bot.send_message(
            chat_id=user_id,
            text=f"👏 Oyun tamamlandı! Bu oyunda {score} puan kazandınız!\n\n"
                 f"🥇 En yüksek skorunuz: {user_best}\n"
                 f"💰 Toplam Biriken Puanınız: {total_score}\n\n"
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
                text="❌ Skor işlenirken bir hata oluştu.",
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