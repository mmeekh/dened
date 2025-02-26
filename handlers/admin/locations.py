import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import Database
from config import LOCATIONS_DIR
from states import LOCATION_PHOTO

logger = logging.getLogger(__name__)
db = Database('shop.db')

async def manage_locations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show location pool management menu"""
    keyboard = [
        [
            InlineKeyboardButton("➕ Konum Ekle", callback_data='add_location'),
            InlineKeyboardButton("📋 Konumları Listele", callback_data='list_locations')
        ],
        [InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]
    ]
    
    message = """📍 Konum Havuzu Yönetimi

Konum havuzu, ürün teslimatı için kullanılan fotoğrafları yönetmenizi sağlar.
Her ürün için birden fazla konum ekleyebilirsiniz.

ℹ️ Yeni konum eklemek için "➕ Konum Ekle" butonunu kullanın."""
    
    await update.callback_query.message.edit_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def add_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start location addition process"""
    # Get list of products
    products = db.get_products()
    if not products:
        await update.callback_query.message.edit_text(
            "❌ Önce ürün eklemelisiniz!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )
        return

    keyboard = []
    for product in products:
        keyboard.append([
            InlineKeyboardButton(
                f"📦 {product[1]}", 
                callback_data=f'select_product_location_{product[0]}'
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 Geri", callback_data='admin_locations')])
    
    await update.callback_query.message.edit_text(
        "Konum eklemek istediğiniz ürünü seçin:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_location_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle location photo upload"""
    if not update.message.photo:
        await update.message.reply_text(
            "❌ Lütfen bir fotoğraf gönderin!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 İptal", callback_data='admin_locations')
            ]])
        )
        return LOCATION_PHOTO

    product_id = context.user_data.get('selected_product_id')
    if not product_id:
        await update.message.reply_text(
            "❌ Bir hata oluştu. Lütfen tekrar deneyin.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )
        return ConversationHandler.END

    try:
        # Get product details
        product = db.get_product(product_id)
        if not product:
            await update.message.reply_text("❌ Ürün bulunamadı!")
            return ConversationHandler.END

        # Create locations directory if not exists
        locations_dir = os.path.join(LOCATIONS_DIR, str(product_id))
        os.makedirs(locations_dir, exist_ok=True)

        # Save photo
        photo = update.message.photo[-1]
        photo_file = await context.bot.get_file(photo.file_id)
        image_path = os.path.join(locations_dir, f'location_{photo.file_id}.jpg')
        await photo_file.download_to_drive(image_path)

        # Add to database
        if db.add_location(product_id, image_path):
            await update.message.reply_text(
                "✅ Konum başarıyla eklendi!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Konum Havuzuna Dön", callback_data='admin_locations')
                ]])
            )
        else:
            await update.message.reply_text(
                "❌ Konum eklenirken bir hata oluştu.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Konum Havuzuna Dön", callback_data='admin_locations')
                ]])
            )

    except Exception as e:
        logger.error(f"Error handling location photo: {e}")
        await update.message.reply_text(
            "❌ Bir hata oluştu. Lütfen tekrar deneyin.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )
    
    return ConversationHandler.END

async def list_locations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of all locations"""
    locations = db.get_all_locations()
    
    if not locations:
        await update.callback_query.message.edit_text(
            "❌ Henüz konum eklenmemiş.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Konum Havuzuna Dön", callback_data='admin_locations')
            ]])
        )
        return
    
    message = "📍 Konum Listesi\n\n"
    keyboard = []
    
    for location in locations:
        product = db.get_product(location['product_id'])
        if not product:
            continue
            
        status = "🔴 Kullanıldı" if location['is_used'] else "🟢 Müsait"
        message += f"📦 {product[1]}\n"
        message += f"📊 Durum: {status}\n"
        message += "───────────────\n"
        
        if not location['is_used']:
            keyboard.append([
                InlineKeyboardButton(
                    f"❌ Sil: {product[1]} Konumu",
                    callback_data=f'delete_location_{location["id"]}'
                )
            ])
    
    keyboard.append([InlineKeyboardButton("🔙 Konum Havuzuna Dön", callback_data='admin_locations')])
    
    try:
        await update.callback_query.message.edit_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error showing locations: {e}")
        simplified_message = "📍 Konum Listesi\n\nKonumları yönetmek için aşağıdaki butonları kullanın."
        await update.callback_query.message.edit_text(
            simplified_message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )