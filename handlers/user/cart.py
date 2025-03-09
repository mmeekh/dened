from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import Database
from config import ADMIN_ID
from states import CART_QUANTITY, DISCOUNT_CODE_INPUT
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)
db = Database('shop.db')

async def show_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's cart with options to remove items, apply discount code, and proceed to checkout"""
    user_id = update.effective_user.id
    cart_items = db.get_cart_items(user_id)

    try:
        if update.callback_query:
            await update.callback_query.message.delete()
        context.user_data.pop('menu_message_id', None)
    except Exception as e:
        logger.error(f"Error deleting message: {e}")
    
    if not cart_items:
        keyboard = [[InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🛒 Sepetiniz boş!",
            reply_markup=reply_markup
        )
        return
    
    # Calculate total before discount
    total = sum(item[2] * item[3] for item in cart_items)  # price * quantity
    total_items = sum(item[3] for item in cart_items)  # sum of quantities
    
    # Check for active discount code in user_data
    discount_info = context.user_data.get('active_discount')
    applied_discount_text = ""
    final_total = total
    
    if discount_info and discount_info.get('valid'):
        discount_percent = discount_info.get('discount_percent', 0)
        discount_amount = (total * discount_percent) / 100
        final_total = total - discount_amount
        applied_discount_text = f"\n💯 İndirim: %{discount_percent} (-{discount_amount:.2f} USDT)"
    
    message = f"""🛒 Sepetim ({total_items} ürün)

📦 Ürünler:
"""
    keyboard = []
    for item in cart_items:
        subtotal = item[2] * item[3]  # price * quantity
        message += f"• {item[1]}\n"
        message += f"  {item[2]} USDT × {item[3]} = {subtotal} USDT\n"
        keyboard.append([
            InlineKeyboardButton(f"❌ Sil: {item[1]}", callback_data=f'remove_cart_{item[0]}')
        ])
    
    message += f"""
───────────────
💰 Toplam Tutar: {total} USDT{applied_discount_text}"""

    if discount_info and discount_info.get('valid'):
        message += f"\n💵 Ödenecek Tutar: {final_total:.2f} USDT"
    
    message += f"""

ℹ️ Minimum sipariş: 20 USDT
ℹ️ Maksimum sipariş: 1000 USDT"""
    
    # Add coupon buttons
    if discount_info and discount_info.get('valid'):
        keyboard.append([InlineKeyboardButton("🎟️ Kuponu Değiştir", callback_data='show_my_coupons')])
    else:
        # Always show available coupons option
        keyboard.append([InlineKeyboardButton("🎟️ Kupon Ekle", callback_data='show_my_coupons')])
    
    # Add checkout button if valid price range
    if cart_items:
        if 20 <= final_total <= 1000:
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
            # Delete user's message
            await update.message.delete()
            
            # Edit the previous message
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
        
        # Get total items in cart
        cart_count = db.get_cart_count(update.effective_user.id)
        
        # Edit previous message with success message
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
        # Delete user's message
        await update.message.delete()
        
        # Edit the previous message
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=last_message_id,
            text="❌ Lütfen geçerli bir sayı girin!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 İptal", callback_data='view_products')
            ]])
        )
        return CART_QUANTITY

async def prompt_discount_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redirect to show_user_coupons instead of showing text input prompt"""
    # We're now redirecting all discount code entry to the coupon selection menu
    await show_user_coupons(update, context)
    return ConversationHandler.END

async def handle_discount_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle discount code input (kept for backward compatibility)"""
    user_id = update.effective_user.id
    coupon_code = update.message.text.strip().upper()
    
    # Delete the user's message to keep the chat clean
    try:
        await update.message.delete()
    except Exception as e:
        logger.error(f"Error deleting message: {e}")
    
    # Validate discount code
    result = db.validate_discount_coupon(coupon_code, user_id)
    
    if result["valid"]:
        # Store discount info in user_data for later use
        context.user_data['active_discount'] = result
        message = f"✅ {result['message']}"
    else:
        # Clear any existing discount
        if 'active_discount' in context.user_data:
            del context.user_data['active_discount']
        message = f"❌ {result['message']}"
    
    # Send a temporary notification
    temp_msg = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message
    )
    
    # Auto-delete after 3 seconds
    await asyncio.sleep(3)
    try:
        await temp_msg.delete()
    except:
        pass
    
    # Show the cart with discount applied
    await show_cart(update, context)
    return ConversationHandler.END

async def show_user_coupons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's available discount coupons with apply option"""
    user_id = update.effective_user.id
    coupons = db.get_user_available_coupons(user_id)
    
    if not coupons:
        await update.callback_query.message.edit_text(
            text="🏷️ Kuponlarım\n\nHenüz indirim kuponunuz bulunmamaktadır. Oyun oynayarak indirim kazanabilirsiniz!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎮 Oyun Oyna", callback_data="games_menu")],
                [InlineKeyboardButton("🔙 Sepete Dön", callback_data="show_cart")]
            ])
        )
        return
    
    message = "🏷️ Kuponlarım\n\nKullanmak istediğiniz kuponu seçin:\n\n"
    keyboard = []
    
    # Get active discount if any
    active_discount = context.user_data.get('active_discount')
    active_coupon_code = active_discount.get('coupon_code') if active_discount and active_discount.get('valid') else None
    
    for code, discount, source, expires in coupons:
        expires_text = ""
        if expires:
            try:
                expiry_date = datetime.strptime(expires, '%Y-%m-%d %H:%M:%S')
                expires_text = f" (Son kullanım: {expiry_date.strftime('%d.%m.%Y')})"
            except:
                pass
        
        # Mark currently active coupon
        active_mark = " ✅ Aktif" if active_coupon_code and active_coupon_code == code else ""
        
        message += f"🎟️ %{discount} indirim{active_mark}\n"
        message += f"📋 Kod: {code}\n"
        message += f"🔍 Kaynak: {source}{expires_text}\n\n"
        
        # Don't add button for already active coupon
        if not (active_coupon_code and active_coupon_code == code):
            keyboard.append([
                InlineKeyboardButton(f"🔄 Kullan: %{discount} indirim", callback_data=f"use_coupon_{code}")
            ])
    
    # Add option to remove discount if one is active
    if active_discount and active_discount.get('valid'):
        keyboard.append([
            InlineKeyboardButton("❌ İndirimi Kaldır", callback_data="remove_discount")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Sepete Dön", callback_data="show_cart")])
    
    await update.callback_query.message.edit_text(
        text=message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def apply_coupon_from_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Apply a coupon selected from the list"""
    user_id = update.effective_user.id
    coupon_code = update.callback_query.data.split("_")[2]
    
    # Validate discount code
    result = db.validate_discount_coupon(coupon_code, user_id)
    
    if result["valid"]:
        # Store coupon code in result for reference
        result['coupon_code'] = coupon_code
        # Store discount info in user_data for later use
        context.user_data['active_discount'] = result
        
        # Send a temporary notification
        await update.callback_query.answer(f"✅ {result['message']}", show_alert=True)
    else:
        # Clear any existing discount
        if 'active_discount' in context.user_data:
            del context.user_data['active_discount']
        
        # Send error notification
        await update.callback_query.answer(f"❌ {result['message']}", show_alert=True)
    
    # Show the cart with discount applied
    await show_cart(update, context)

async def remove_discount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove applied discount"""
    # Clear the active discount
    if 'active_discount' in context.user_data:
        del context.user_data['active_discount']
    
    # Notify user
    await update.callback_query.answer("✅ İndirim kaldırıldı", show_alert=True)
    
    # Show updated cart
    await show_cart(update, context)