import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def create_flappy_weed_game_artifact(update: Update, context: ContextTypes.DEFAULT_TYPE, game_session: str):
    """Flappy Weed oyun bileşeni için React artifact oluştur"""
    try:
        # React bileşeni için HTML içeriği oluştur
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Flappy Weed</title>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/react/18.2.0/umd/react.production.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/react-dom/18.2.0/umd/react-dom.production.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/tone/14.8.49/Tone.min.js"></script>
            <style>
                body {{ margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; height: 100vh; background-color: #f0f0f0; }}
                #game-container {{ width: 320px; height: 480px; position: relative; }}
                canvas {{ display: block; }}
            </style>
        </head>
        <body>
            <div id="game-container"></div>
            
            <script>
                // React bileşeni burada
                const FlappyWeedGame = () => {{
                    // Canvas size
                    const canvasWidth = 320;
                    const canvasHeight = 480;
                    
                    // Burada React bileşeninizin tüm kodu yer alacak
                    // ...
                }};
                
                // Bileşeni render et
                ReactDOM.render(React.createElement(FlappyWeedGame), document.getElementById('game-container'));
            </script>
        </body>
        </html>
        """
        
        # Oyunu başlatmak için butonu göster
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🎮 Oyun yüklendi! Başlamak için aşağıdaki butona tıklayın.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ Oyuna Başla", web_app={"url": f"https://sizin-web-siteniz.com/flappy-weed?session={game_session}"})],
                [InlineKeyboardButton("🔙 Oyun Menüsü", callback_data='games_menu')]
            ])
        )
        
    except Exception as e:
        logger.error(f"Oyun bileşeni oluştururken hata: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Oyun yüklenirken bir hata oluştu.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Oyun Menüsü", callback_data='games_menu')
            ]])
        )