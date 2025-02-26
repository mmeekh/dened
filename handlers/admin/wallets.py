from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import Database
from states import WALLET_INPUT
import logging

logger = logging.getLogger(__name__)
db = Database('shop.db')

async def manage_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show wallet management menu"""
    # Get wallet statistics
    available_count = db.get_available_wallet_count()
    in_use_count = db.get_in_use_wallet_count()
    total_count = db.get_total_wallet_count()
    
    keyboard = [
        [
            InlineKeyboardButton("➕ Cüzdan Ekle", callback_data='add_wallet'),
            InlineKeyboardButton("📋 Cüzdanları Listele", callback_data='list_wallets')
        ],
        [InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]
    ]
    
    message = f"""👛 Cüzdan Havuzu Yönetimi

📊 Cüzdan İstatistikleri:
✅ Müsait Cüzdan: {available_count}
🔄 Kullanımda: {in_use_count}
📊 Toplam: {total_count}

ℹ️ Yeni cüzdan eklemek için "➕ Cüzdan Ekle" butonunu kullanın."""
    
    await update.callback_query.message.edit_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def add_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start wallet addition process"""
    await update.callback_query.message.edit_text(
        """🏦 Yeni TRC20 Cüzdan Ekle

Lütfen TRC20 cüzdan adresini girin:

⚠️ Önemli:
• Sadece TRC20 cüzdan adresleri kabul edilir
• Adres 'T' ile başlamalı ve 34 karakter olmalı
• Yanlış ağ/adres kullanımı fonların kaybına neden olabilir""",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 İptal", callback_data='admin_wallets')
        ]])
    )
    return WALLET_INPUT

async def handle_wallet_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the wallet address input"""
    wallet_address = update.message.text.strip()
    user_id = update.effective_user.id
    
    try:
        await update.message.delete()
    except Exception as e:
        logger.error(f"Error deleting user message: {e}")
    
    # Basic TRC20 address validation
    if not wallet_address.startswith('T') or len(wallet_address) != 34:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Geçersiz TRC20 cüzdan adresi! Lütfen tekrar deneyin.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Cüzdan Havuzuna Dön", callback_data='admin_wallets')
            ]])
        )
        return ConversationHandler.END
    
    success = db.add_wallet(wallet_address)
    if success:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="✅ Cüzdan başarıyla eklendi!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Cüzdan Havuzuna Dön", callback_data='admin_wallets')
            ]])
        )
    else:  # Address might already exist
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Bu cüzdan adresi zaten havuzda mevcut veya eklenirken bir hata oluştu.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Cüzdan Havuzuna Dön", callback_data='admin_wallets')
            ]])
        )
    
    return ConversationHandler.END

async def list_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of all wallets"""
    query = update.callback_query
    wallets = db.get_all_wallets()
    
    if not wallets:
        await query.message.edit_text(
            "❌ Havuzda cüzdan bulunmamaktadır.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Cüzdan Havuzuna Dön", callback_data='admin_wallets')
            ]])
        )
        return
    
    message = "📋 Cüzdan Havuzu\n\n"
    keyboard = []
    
    for wallet in wallets:
        wallet_id, address, in_use = wallet[0], wallet[1], wallet[2]
        status = "🔴 Kullanımda" if in_use else "🟢 Müsait"
        
        message += f"🏦 {address[:8]}...{address[-8:]}\n"
        message += f"📊 Durum: {status}\n"
        message += "───────────────\n"
        
        if not in_use:
            keyboard.append([
                InlineKeyboardButton(
                    f"❌ Sil: {address[:8]}...",
                    callback_data=f'delete_wallet_{wallet_id}'
                )
            ])
    
    keyboard.append([InlineKeyboardButton("🔙 Cüzdan Havuzuna Dön", callback_data='admin_wallets')])
    
    try:
        await query.message.edit_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error showing wallets: {e}")
        # If message is too long, send a simplified version
        simplified_message = "📋 Cüzdan Havuzu\n\nCüzdanları yönetmek için aşağıdaki butonları kullanın."
        await query.message.edit_text(
            simplified_message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )