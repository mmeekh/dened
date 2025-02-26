import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import Database
from states import CATEGORY_NAME, CATEGORY_DESCRIPTION

logger = logging.getLogger(__name__)
db = Database('shop.db')

async def manage_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show category management menu"""
    categories = db.get_categories()
    
    keyboard = [
        [InlineKeyboardButton("➕ Kategori Ekle", callback_data='add_category')]
    ]
    
    if categories:
        message = "📁 Kategoriler:\n\n"
        for category in categories:
            message += f"🔸 {category[1]}\n"
            if category[2]:  # If has description
                message += f"📝 {category[2]}\n"
            message += "───────────────\n"
            
            keyboard.append([
                InlineKeyboardButton(f"✏️ {category[1]}", callback_data=f'edit_category_{category[0]}'),
                InlineKeyboardButton("❌", callback_data=f'delete_category_{category[0]}')
            ])
    else:
        message = "📂 Henüz kategori bulunmamaktadır."
        
    keyboard.append([InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')])
    
    await update.callback_query.message.edit_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def add_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start category addition process"""
    await update.callback_query.message.edit_text(
        "Yeni kategori adını girin:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 İptal", callback_data='manage_categories')
        ]])
    )
    return CATEGORY_NAME

async def handle_category_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle category name input"""
    context.user_data['category_name'] = update.message.text
    
    await update.message.reply_text(
        "Kategori açıklamasını girin (veya '-' ile geçin):",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 İptal", callback_data='manage_categories')
        ]])
    )
    
    return CATEGORY_DESCRIPTION

async def handle_category_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle category description input"""
    description = None if update.message.text == '-' else update.message.text
    name = context.user_data.get('category_name')
    
    if not name:
        await update.message.reply_text(
            "❌ Bir hata oluştu. Lütfen tekrar deneyin.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Kategorilere Dön", callback_data='manage_categories')
            ]])
        )
        return ConversationHandler.END
    
    if db.add_category(name, description):
        message = f"✅ Kategori başarıyla eklendi!\n\n"
        message += f"📁 {name}\n"
        if description:
            message += f"📝 {description}"
    else:
        message = "❌ Kategori eklenirken bir hata oluştu."
    
    keyboard = [[InlineKeyboardButton("🔙 Kategorilere Dön", callback_data='manage_categories')]]
    await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
    
    return ConversationHandler.END

async def delete_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a category"""
    query = update.callback_query
    category_id = int(query.data.split('_')[2])
    
    if db.delete_category(category_id):
        message = "✅ Kategori başarıyla silindi!"
    else:
        message = "❌ Kategori silinirken bir hata oluştu."
    
    keyboard = [[InlineKeyboardButton("🔙 Kategorilere Dön", callback_data='manage_categories')]]
    await query.message.edit_text(message, reply_markup=InlineKeyboardMarkup(keyboard))