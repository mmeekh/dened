import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import Database
from config import PRODUCTS_DIR
from states import *
import os

logger = logging.getLogger(__name__)
db = Database('shop.db')

async def add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start product addition process"""
    message = "Ürün adını girin:"
    keyboard = [[InlineKeyboardButton("🔙 İptal", callback_data='admin_products')]]
    
    await update.callback_query.message.edit_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return PRODUCT_NAME

async def handle_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle product name input"""
    context.user_data['product_data'] = {'name': update.message.text}
    
    sent_message = await update.message.reply_text(
        "Ürün açıklamasını girin:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 İptal", callback_data='admin_products')
        ]])
    )
    
    context.user_data['current_message_id'] = sent_message.message_id
    await update.message.delete()
    
    return PRODUCT_DESCRIPTION

async def handle_product_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle product description input"""
    context.user_data['product_data']['description'] = update.message.text
    
    current_message_id = context.user_data.get('current_message_id')
    if current_message_id:
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=current_message_id
            )
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
    
    sent_message = await update.message.reply_text(
        "Ürün fiyatını USDT olarak girin (sadece sayı):",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 İptal", callback_data='admin_products')
        ]])
    )
    
    context.user_data['current_message_id'] = sent_message.message_id
    await update.message.delete()
    
    return PRODUCT_PRICE

async def handle_product_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle product price input"""
    try:
        price = float(update.message.text)
        if price <= 0:
            raise ValueError("Price must be positive")
            
        context.user_data['product_data']['price'] = price
        
        current_message_id = context.user_data.get('current_message_id')
        if current_message_id:
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=current_message_id
                )
            except Exception as e:
                logger.error(f"Error deleting message: {e}")
        
        sent_message = await update.message.reply_text(
            "Başlangıç stok miktarını girin:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 İptal", callback_data='admin_products')
            ]])
        )
        
        context.user_data['current_message_id'] = sent_message.message_id
        await update.message.delete()
        
        return PRODUCT_STOCK
        
    except ValueError:
        sent_message = await update.message.reply_text(
            "❌ Lütfen geçerli bir sayı girin!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 İptal", callback_data='admin_products')
            ]])
        )
        
        context.user_data['current_message_id'] = sent_message.message_id
        await update.message.delete()
        
        return PRODUCT_PRICE

async def handle_product_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle product stock input"""
    try:
        stock = int(update.message.text)
        if stock < 0:
            raise ValueError("Stock cannot be negative")
            
        context.user_data['product_data']['stock'] = stock
        
        current_message_id = context.user_data.get('current_message_id')
        if current_message_id:
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=current_message_id
                )
            except Exception as e:
                logger.error(f"Error deleting message: {e}")
        
        sent_message = await update.message.reply_text(
            "Ürün fotoğrafını gönderin:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 İptal", callback_data='admin_products')
            ]])
        )
        
        context.user_data['current_message_id'] = sent_message.message_id
        await update.message.delete()
        
        return PRODUCT_IMAGE
        
    except ValueError:
        sent_message = await update.message.reply_text(
            "❌ Lütfen geçerli bir sayı girin!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 İptal", callback_data='admin_products')
            ]])
        )
        
        context.user_data['current_message_id'] = sent_message.message_id
        await update.message.delete()
        
        return PRODUCT_STOCK

async def handle_product_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle product image upload"""
    if update.message.photo:
        try:
            product_data = context.user_data['product_data']
            product_dir = os.path.join(PRODUCTS_DIR, product_data['name'])
            os.makedirs(product_dir, exist_ok=True)
            
            photo = update.message.photo[-1]
            photo_file = await context.bot.get_file(photo.file_id)
            image_path = os.path.join(product_dir, 'product.jpg')
            await photo_file.download_to_drive(image_path)
            
            success = db.add_product(
                name=product_data['name'],
                description=product_data['description'],
                price=product_data['price'],
                image_path=image_path,
                stock=product_data.get('stock', 0)
            )
            
            del context.user_data['product_data']
            
            if success:
                message = "✅ Ürün başarıyla eklendi!"
            else:
                message = "❌ Ürün eklenirken bir hata oluştu."
            
            keyboard = [[InlineKeyboardButton("🔙 Ürün Yönetimine Dön", callback_data='admin_products')]]
            await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
            
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Error adding product: {e}")
            await update.message.reply_text(
                "❌ Ürün eklenirken bir hata oluştu.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Ürün Yönetimine Dön", callback_data='admin_products')
                ]])
            )
            return ConversationHandler.END
    else:
        await update.message.reply_text(
            "Lütfen bir fotoğraf gönderin:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 İptal", callback_data='admin_products')
            ]])
        )
        return PRODUCT_IMAGE
async def manage_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show product management menu"""
    keyboard = [
        [
            InlineKeyboardButton("➕ Ürün Ekle", callback_data='add_product')
        ],
        [InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]
    ]
    
    products = db.get_products()
    if not products:
        message = "📦 Henüz ürün bulunmamaktadır."
    else:
        message = "📦 Ürün Yönetimi\n\n"
        for product in products:
            stock_status = "✅" if product[5] > 0 else "❌"
            
            message += f"🔸 {product[1]}\n"
            message += f"💰 {product[3]} USDT\n"
            message += f"📦 Stok: {stock_status} ({product[5]})\n"
            message += "───────────────\n"
            
            keyboard.insert(-1, [
                InlineKeyboardButton(f"✏️ {product[1]}", callback_data=f'edit_product_{product[0]}'),
                InlineKeyboardButton("❌", callback_data=f'delete_product_{product[0]}')
            ])
    
    await update.callback_query.message.edit_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: int):
    """Show edit menu for a specific product"""
    product = db.get_product(product_id)
    if not product:
        await update.callback_query.message.edit_text(
            "❌ Ürün bulunamadı!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ürün Yönetimine Dön", callback_data='admin_products')
            ]])
        )
        return

    message = f"""📦 {product[1]}
💰 {product[3]} USDT
📝 {product[2]}

Düzenlemek istediğiniz alanı seçin:"""

    keyboard = [
        [InlineKeyboardButton("✏️ Ürün Adı", callback_data='edit_name')],
        [InlineKeyboardButton("📝 Açıklama", callback_data='edit_description')],
        [InlineKeyboardButton("💰 Fiyat", callback_data='edit_price')],
        [InlineKeyboardButton("🔙 Ürün Yönetimine Dön", callback_data='admin_products')]
    ]

    await update.callback_query.message.edit_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_delete_product(update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: int):
    """Handle product deletion"""
    product = db.get_product(product_id)

    if not product:
        await update.callback_query.message.edit_text(
            "❌ Ürün bulunamadı!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ürün Yönetimine Dön", callback_data='admin_products')
            ]])
        )
        return

    # Delete product image if exists
    if product[4] and os.path.exists(product[4]):
        try:
            os.remove(product[4])
            # Try to remove product directory if empty
            product_dir = os.path.dirname(product[4])
            if os.path.exists(product_dir) and not os.listdir(product_dir):
                os.rmdir(product_dir)
        except Exception as e:
            logger.error(f"Error deleting product image: {e}")

    # Delete product from database
    if db.delete_product(product_id):
        message = f"✅ {product[1]} başarıyla silindi!"
    else:
        message = "❌ Ürün silinirken bir hata oluştu."

    await update.callback_query.message.edit_text(
        message,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Ürün Yönetimine Dön", callback_data='admin_products')
        ]])
    )

async def handle_edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle product name edit"""
    product_id = context.user_data.get('edit_product_id')
    if not product_id:
        await update.message.reply_text(
            "❌ Bir hata oluştu. Lütfen tekrar deneyin.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ürün Yönetimine Dön", callback_data='admin_products')
            ]])
        )
        return ConversationHandler.END
    
    new_name = update.message.text
    if db.update_product_name(product_id, new_name):
        message = "✅ Ürün adı başarıyla güncellendi!"
    else:
        message = "❌ Ürün adı güncellenirken bir hata oluştu."
    
    await update.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Ürün Yönetimine Dön", callback_data='admin_products')
        ]])
    )
    
    return ConversationHandler.END

async def handle_edit_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle product description edit"""
    product_id = context.user_data.get('edit_product_id')
    if not product_id:
        await update.message.reply_text(
            "❌ Bir hata oluştu. Lütfen tekrar deneyin.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ürün Yönetimine Dön", callback_data='admin_products')
            ]])
        )
        return ConversationHandler.END
    
    new_description = update.message.text
    if db.update_product_description(product_id, new_description):
        message = "✅ Ürün açıklaması başarıyla güncellendi!"
    else:
        message = "❌ Ürün açıklaması güncellenirken bir hata oluştu."
    
    await update.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Ürün Yönetimine Dön", callback_data='admin_products')
        ]])
    )
    
    return ConversationHandler.END

async def handle_edit_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle product price edit"""
    product_id = context.user_data.get('edit_product_id')
    if not product_id:
        await update.message.reply_text(
            "❌ Bir hata oluştu. Lütfen tekrar deneyin.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ürün Yönetimine Dön", callback_data='admin_products')
            ]])
        )
        return ConversationHandler.END
    
    try:
        new_price = float(update.message.text)
        if new_price <= 0:
            raise ValueError("Price must be positive")
            
        if db.update_product_price(product_id, new_price):
            message = "✅ Ürün fiyatı başarıyla güncellendi!"
        else:
            message = "❌ Ürün fiyatı güncellenirken bir hata oluştu."
        
        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ürün Yönetimine Dön", callback_data='admin_products')
            ]])
        )
        
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text(
            "❌ Lütfen geçerli bir fiyat girin!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 İptal", callback_data='admin_products')
            ]])
        )
        return EDIT_PRICE

async def handle_stock_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle stock quantity input"""
    try:
        quantity = int(update.message.text)
        stock_change = context.user_data.get('stock_change')
        
        if not stock_change:
            await update.message.reply_text(
                "❌ Bir hata oluştu. Lütfen tekrar deneyin.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Ürün Yönetimine Dön", callback_data='admin_products')
                ]])
            )
            return ConversationHandler.END
        
        product_id = stock_change['product_id']
        action = stock_change['action']
        
        # Update stock
        if action == 'add':
            success = db.update_product_stock(product_id, quantity)
        else:  # remove
            success = db.update_product_stock(product_id, -quantity)
        
        if success:
            product = db.get_product(product_id)
            message = f"✅ Stok güncellendi!\n\n"
            message += f"📦 {product[1]}\n"
            message += f"📊 Yeni Stok: {product[5]}"
        else:
            message = "❌ Stok güncellenirken bir hata oluştu."
        
        keyboard = [[InlineKeyboardButton("🔙 Ürün Yönetimine Dön", callback_data='admin_products')]]
        await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
        
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text(
            "❌ Lütfen geçerli bir sayı girin!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 İptal", callback_data='admin_products')
            ]])
        )
        return STOCK_CHANGE