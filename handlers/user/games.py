import logging
import json
import uuid
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
        remaining_games = db.get_remaining_daily_games(user_id)
        
        keyboard = [
            [InlineKeyboardButton("🍀 Flappy Weed", callback_data='play_flappy_weed')],
            [InlineKeyboardButton("🏆 Skor Tablosu", callback_data='show_leaderboard')],
            [InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]
        ]
        
        message = f"""🎮 Oyun Menüsü

🍀 Flappy Weed oyununda yüksek puan yap, indirim kazanmaya hak kazan!

🎯 Günlük oyun hakkı: {remaining_games}/3
🏆 500+ puan = %5 indirim
🏆 1000+ puan = %10 indirim
🏆 2000+ puan = %15 indirim

En yüksek skorlarınla liderlik tablosuna gir ve özel ödüller kazan!"""
        
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
        # Oyun oturumu oluştur
        game_session = str(uuid.uuid4())
        
        # Oyun açıklaması ve başlatma butonuyla mesaj gönder
        await update.callback_query.message.edit_text(
            text=f"🍀 Flappy Weed Oyunu\n\n"
                 f"Nasıl Oynanır:\n"
                 f"- Ekrana tıklayarak weed parçasını zıplat\n"
                 f"- Borulardan kaçın ve mümkün olduğunca ilerle\n"
                 f"- Her bir borudan geçiş 1 puan kazandırır\n\n"
                 f"🔊 Ses efektleri için telefonunuzun sesini açın!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ Oyunu Başlat", callback_data=f'start_flappy_{game_session}')],
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
    """Flappy Weed React bileşenini göster"""
    try:
        user_id = update.effective_user.id
        game_session = update.callback_query.data.split('_')[2]
        
        game_url = f"https://sanemdens.github.io/-random-game-repo/game.html?session={game_session}"
        
        # Mesajı düzenle ve oyun bağlantısı gönder
        await update.callback_query.message.edit_text(
            text="🎮 Flappy Weed oyununu açmak için aşağıdaki butona tıklayın:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎮 Oyunu Oyna", web_app={"url": game_url})],
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
    """Oyun skorunu kaydet"""
    try:
        user_id = update.effective_user.id
        
        # WebApp veri alımıyla veya başlatma komutundan gelen veriyi işle
        if update.message and update.message.web_app_data:
            # WebApp'ten gelen veri
            data = json.loads(update.message.web_app_data.data)
            game_session = data.get('session')
            score = data.get('score', 0)
        elif update.message and update.message.text and 'save_score_' in update.message.text:
            # URL'den gelen veri
            parts = update.message.text.split('save_score_')[1].split('_')
            game_session = parts[0]
            score = int(parts[1])
        else:
            # Callback verisi
            data = json.loads(update.callback_query.data.replace('save_score_', ''))
            game_session = data.get('session')
            score = data.get('score', 0)
        
        # Skoru veritabanına kaydet
        if db.save_game_score(user_id, game_session, score):
            # Skor başarıyla kaydedildi
            
            # Kupon kazanıldı mı kontrol et
            discount = 0
            if score >= 2000:
                discount = 15
            elif score >= 1000:
                discount = 10
            elif score >= 500:
                discount = 5
                
            if discount > 0:
                # Kupon oluştur
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
                
    except Exception as e:
        logger.error(f"Skor kaydedilirken hata: {e}")
        # Hatayı kullanıcıya bildirmeden sessizce logla

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skor tablosunu göster"""
    try:
        # En yüksek 10 skoru getir
        scores = db.get_top_scores(10)
        user_id = update.effective_user.id
        
        # Kullanıcının kendi en yüksek skoru
        user_best = db.get_user_best_score(user_id)
        
        if not scores:
            message = "🏆 Skor Tablosu\n\nHenüz kimse oyun oynamamış. İlk skor senin olabilir!"
        else:
            message = "🏆 Flappy Weed Skor Tablosu - En İyiler\n\n"
            
            for i, (score_user_id, username, score, date) in enumerate(scores):
                medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"{i+1}."
                display_name = username or f"Kullanıcı {score_user_id}"
                is_you = " (Sen)" if score_user_id == user_id else ""
                
                message += f"{medal} {display_name}{is_you}: {score} puan ({date})\n"
            
            if user_best and all(user_id != uid for uid, _, _, _ in scores):
                message += f"\n🎮 Senin en yüksek skorun: {user_best} puan"
        
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