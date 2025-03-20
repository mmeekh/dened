from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import Database
from states import WALLET_INPUT
import logging

logger = logging.getLogger(__name__)
db = Database('shop.db')

async def manage_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show improved wallet management menu with accurate counts"""
    # Doğru cüzdan istatistiklerini hesapla
    try:
        # Kullanıcılara atanmış cüzdan sayısını al (user_wallets tablosundan)
        db.cur.execute("SELECT COUNT(DISTINCT wallet_id) FROM user_wallets")
        assigned_wallets = db.cur.fetchone()[0] or 0
        
        # Toplam cüzdan sayısını al
        db.cur.execute("SELECT COUNT(*) FROM wallets")
        total_wallets = db.cur.fetchone()[0] or 0
        
        # İşlemde olan ama kullanıcıya atanmamış cüzdanları bul
        db.cur.execute("""
            SELECT COUNT(*) FROM wallets w
            WHERE w.in_use = 1
            AND NOT EXISTS (
                SELECT 1 FROM user_wallets uw 
                WHERE uw.wallet_id = w.id
            )
        """)
        temporary_in_use = db.cur.fetchone()[0] or 0
        
        # Gerçekten müsait olan cüzdan sayısı
        available_wallets = total_wallets - assigned_wallets - temporary_in_use
    except Exception as e:
        logger.error(f"Error calculating wallet stats: {e}")
        # Sorun durumunda eski yönteme geri dön
        available_wallets = db.get_available_wallet_count()
        temporary_in_use = db.get_in_use_wallet_count()
        total_wallets = db.get_total_wallet_count()
        assigned_wallets = 0  # Bunu bilemeyiz sorun olunca
    
    # Müsait cüzdan kalmadıysa uyarı
    warning = ""
    if available_wallets == 0:
        warning = "\n\n⚠️ DİKKAT: Müsait cüzdan kalmadı! Acilen yeni cüzdan ekleyin."
    elif available_wallets < 5:
        warning = f"\n\n⚠️ Uyarı: Sadece {available_wallets} müsait cüzdan kaldı. Yeni cüzdan eklemeniz önerilir."
    
    keyboard = [
        [
            InlineKeyboardButton("➕ Cüzdan Ekle", callback_data='add_wallet'),
            InlineKeyboardButton("📋 Cüzdanları Listele", callback_data='list_wallets')
        ],
        [
            InlineKeyboardButton("🔄 Cüzdanları Serbest Bırak", callback_data='release_all_wallets')
        ],
        [InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]
    ]
    
    message = f"""👛 Cüzdan Havuzu Yönetimi

📊 Cüzdan İstatistikleri:
🟢 Müsait Cüzdan: {available_wallets}
👤 Kullanıcıya Atanmış: {assigned_wallets}
🔴 Geçici Kullanımda: {temporary_in_use}
📊 Toplam: {total_wallets}{warning}

ℹ️ Yeni cüzdan eklemek için "➕ Cüzdan Ekle" butonunu kullanın.
ℹ️ Kullanımdaki cüzdanları görmek ve yönetmek için "📋 Cüzdanları Listele" butonunu kullanın.
ℹ️ Takılı kalan cüzdanları serbest bırakmak için "🔄 Cüzdanları Serbest Bırak" butonunu kullanın."""
    
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
async def release_all_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Release all in_use wallets for administrator"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Cüzdanları serbest bırak
        db.cur.execute("UPDATE wallets SET in_use = 0")
        db.conn.commit()
        
        count = db.cur.rowcount
        
        await query.message.edit_text(
            f"✅ Toplam {count} cüzdan başarıyla serbest bırakıldı.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Cüzdan Havuzuna Dön", callback_data='admin_wallets')
            ]])
        )
    except Exception as e:
        logger.error(f"Error releasing all wallets: {e}")
        await query.message.edit_text(
            "❌ Cüzdanlar serbest bırakılırken bir hata oluştu.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Cüzdan Havuzuna Dön", callback_data='admin_wallets')
            ]])
        )
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
    """Show list of all wallets with user assignment information"""
    query = update.callback_query
    
    try:
        # Cüzdan-kullanıcı ilişkilerini göster
        db.cur.execute("""
            SELECT 
                w.id, 
                w.address, 
                w.in_use,
                uw.user_id,
                (SELECT COUNT(*) FROM purchase_requests WHERE wallet = w.address) as usage_count,
                (SELECT 
                    CASE 
                        WHEN COUNT(*) > 0 THEN MAX(created_at) 
                        ELSE NULL 
                    END 
                FROM purchase_requests WHERE wallet = w.address) as last_used_date
            FROM wallets w
            LEFT JOIN user_wallets uw ON w.id = uw.wallet_id
            ORDER BY w.in_use DESC, uw.user_id IS NOT NULL DESC, last_used_date DESC
        """)
        wallets = db.cur.fetchall()
    except Exception as e:
        logger.error(f"Error fetching wallets: {e}")
        wallets = []
    
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
    
    # Kullanımda, atanmış ve müsait cüzdan sayılarını hesapla
    in_use_count = sum(1 for wallet in wallets if wallet[2])
    assigned_count = sum(1 for wallet in wallets if wallet[3] is not None)
    available_count = len(wallets) - assigned_count
    
    message += f"📊 Özet: {len(wallets)} cüzdan ({available_count} müsait, {assigned_count} atanmış)\n\n"
    
    for i, wallet in enumerate(wallets, 1):
        wallet_id, address, in_use, user_id, usage_count, last_used = wallet
        
        if user_id is not None:
            status = f"👤 Kullanıcıya Atandı: {user_id}"
        elif in_use:
            status = "🔴 Kullanımda (Geçici)"
        else:
            status = "🟢 Müsait"
        
        message += f"{i}. 🏦 {address[:8]}...{address[-8:]}\n"
        message += f"📊 Durum: {status}\n"
        
        if usage_count and usage_count > 0:
            message += f"🔄 Kullanım: {usage_count} kez\n"
            
        if last_used:
            message += f"⏱️ Son Kullanım: {last_used}\n"
            
        message += "───────────────\n"
        
        # Sadece müsait (kullanıcıya atanmamış ve in_use=0) cüzdanlar silinebilir
        if not in_use and user_id is None:
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
        logger.error(f"Error showing wallets, message too long: {e}")
        # Mesaj çok uzunsa, kısaltılmış bir versiyonunu göster
        simplified_message = "📋 Cüzdan Havuzu\n\n"
        simplified_message += f"📊 Özet: {len(wallets)} cüzdan ({available_count} müsait, {assigned_count} atanmış)\n\n"
        simplified_message += "Cüzdanları yönetmek için aşağıdaki butonları kullanın."
        
        await query.message.edit_text(
            simplified_message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )