from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import Database
from config import ADMIN_ID
from states import CART_QUANTITY
import logging

logger = logging.getLogger(__name__)
db = Database('shop.db')

async def show_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's cart"""
    user_id = update.effective_user.id
    cart_items = db.get_cart_items(user_id)

    try:
        await update.callback_query.message.delete()
    except Exception as e:
        logger.error(f"Error deleting message: {e}")

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

    total = sum(item[2] * item[3] for item in cart_items)
    total_items = sum(item[3] for item in cart_items)
    
    message = f"""🛒 Sepetim ({total_items} ürün)

📦 Ürünler:
"""
    keyboard = []
    
    for item in cart_items:
        subtotal = item[2] * item[3]
        message += f"• {item[1]}\n"
        message += f"  {item[2]} USDT × {item[3]} = {subtotal} USDT\n"
        keyboard.append([
            InlineKeyboardButton(f"❌ Sil: {item[1]}", callback_data=f'remove_cart_{item[0]}')
        ])
    
    message += f"""
───────────────
💰 Toplam Tutar: {total} USDT

ℹ️ Minimum sipariş: 20 USDT
ℹ️ Maksimum sipariş: 1000 USDT"""
    
    if cart_items:
        if 20 <= total <= 1000:
            keyboard.append([InlineKeyboardButton("💳 Ödemeye Geç", callback_data='request_purchase')])
        else:
            message += "\n\n❌ Tutar sınırlar dışında!"
            
    keyboard.append([InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        reply_markup=reply_markup
    )

async def handle_add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle adding product to cart"""
    query = update.callback_query
    user_id = update.effective_user.id
    
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
        sent_message = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"📦 {product[1]} için miktar giriniz:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 İptal", callback_data='view_products')
            ]])
        )
        context.user_data['last_bot_message_id'] = sent_message.message_id
        
        try:
            await query.message.delete()
        except Exception as e:
            logger.error(f"Error deleting old message: {e}")
    
    return CART_QUANTITY

async def handle_cart_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quantity input for cart item"""
    try:
        quantity = int(update.message.text)
        last_message_id = context.user_data.get('last_bot_message_id')
        
        if not last_message_id:
            await update.message.delete()
            return ConversationHandler.END
        
        if quantity <= 0:
            await update.message.delete()
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
        
        db.add_to_cart(update.effective_user.id, product_id, quantity)
        await update.message.delete()
        
        cart_count = db.get_cart_count(update.effective_user.id)
        
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
        await update.message.delete()
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=last_message_id,
            text="❌ Lütfen geçerli bir sayı girin!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 İptal", callback_data='view_products')
            ]])
        )
        return CART_QUANTITY