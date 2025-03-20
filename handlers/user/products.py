from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import Database
import os
import logging

logger = logging.getLogger(__name__)
db = Database('shop.db')

async def show_products_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show products menu"""
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
    """Show all products"""
    products = db.get_products()
    
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

    for product in products:
        message = f"🔸 {product[1]}\n"
        message += f"📝 {product[2]}\n"
        message += f"💰 {product[3]} USDT"
        
        keyboard = [
            [InlineKeyboardButton(f"🛒 Sepete Ekle", callback_data=f'add_to_cart_{product[0]}')],
        ]
        
        if product == products[-1]:
            keyboard.append([InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')])
        
        try:
            if product[4] and os.path.exists(product[4]):
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=open(product[4], 'rb'),
                    caption=message,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=message,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        except Exception as e:
            logger.error(f"Error sending product {product[1]}: {e}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )