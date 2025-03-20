import logging
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def cleanup_previous_message(update, context):
    """Delete the previous menu message if it exists"""
    # Get previous message ID
    prev_message_id = context.user_data.get('menu_message_id')
    
    if prev_message_id:
        try:
            # Try to delete the previous message
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=prev_message_id
            )
            # Clear from user_data after deletion
            context.user_data.pop('menu_message_id', None)
        except Exception as e:
            # Log error but continue
            logger.debug(f"Could not delete previous menu message: {e}")
async def show_generic_menu(update, context, text, reply_markup=None):
    """Show a menu, maintaining UI consistency by cleaning up previous messages"""
    # Always clean up previous messages first
    await cleanup_previous_message(update, context)
    
    # Handle callback query answer if present
    if update.callback_query:
        try:
            await update.callback_query.answer()
        except Exception as e:
            logger.debug(f"Error answering callback query: {e}")
    
    # Handle user message deletion if present
    if update.message:
        try:
            await update.message.delete()
        except Exception as e:
            logger.debug(f"Could not delete user message: {e}")
    
    # Send new message
    sent_message = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=reply_markup
    )
    
    # Store the message ID
    context.user_data['menu_message_id'] = sent_message.message_id
    
    return sent_message
async def cleanup_old_messages(bot, chat_id, message_ids=None, context=None):
    """
    Clean up old messages to keep the chat tidy
    
    Args:
        bot: The bot instance
        chat_id: The chat ID where messages should be deleted
        message_ids: Optional list of specific message IDs to delete
        context: Optional context with user_data containing tracked messages
    """
    deleted_count = 0
    
    # Delete specific message IDs if provided
    if message_ids:
        for msg_id in message_ids:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=msg_id)
                deleted_count += 1
            except Exception as e:
                logger.debug(f"Could not delete message {msg_id}: {e}")
                
    # Delete tracked messages in context if provided
    if context and hasattr(context, 'user_data'):
        tracked_keys = [k for k in context.user_data.keys() if k.endswith('_message_id')]
        
        for key in tracked_keys:
            msg_id = context.user_data.get(key)
            if msg_id:
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=msg_id)
                    # Remove the key after successful deletion
                    context.user_data.pop(key)
                    deleted_count += 1
                except Exception as e:
                    logger.debug(f"Could not delete tracked message {key}: {e}")
    
    return deleted_count
async def show_photo_message(update, context, photo_path, caption, reply_markup=None):
    """Send a photo message with consistent UI management"""
    # Clean up previous message
    await cleanup_previous_message(update, context)
    
    # Send the photo
    sent_message = await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=open(photo_path, 'rb'),
        caption=caption,
        reply_markup=reply_markup
    )
    
    # Store message ID for future cleanup
    context.user_data['menu_message_id'] = sent_message.message_id
    
    return sent_message
async def show_media_menu(update: Update, context: ContextTypes.DEFAULT_TYPE,
                      photo_path: str, caption: str, 
                      reply_markup: InlineKeyboardMarkup = None):
    """
    Resimli menü gösterici - resim içeren menüler için
    
    Args:
        update: Telegram update nesnesi
        context: Telegram context nesnesi
        photo_path: Resim dosyası yolu
        caption: Resim üzerindeki açıklama
        reply_markup: Klavye düğmeleri (opsiyonel)
    """
    try:
        # Bu bir formatı değiştirme durumu (metin -> resim), 
        # bu yüzden mevcut mesajı silip yeni resimli mesaj göndermek daha güvenli
        current_message_id = context.user_data.get('menu_message_id')
        
        # Eğer varsa mevcut mesajı sil
        if current_message_id:
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=current_message_id
                )
            except Exception as e:
                logger.debug(f"Eski mesajı silerken hata: {e}")
        
        # Kullanıcı mesajını sil
        if update.message:
            try:
                await update.message.delete()
            except Exception as e:
                logger.debug(f"Kullanıcı mesajını silerken hata: {e}")
                
        # Yeni resimli mesaj gönder
        try:
            sent_message = await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=open(photo_path, 'rb'),
                caption=caption,
                reply_markup=reply_markup
            )
            # Yeni mesaj ID'sini kaydet
            context.user_data['menu_message_id'] = sent_message.message_id
        except Exception as photo_e:
            logger.error(f"Resim gönderirken hata: {photo_e}")
            # Resim gönderilemezse, metin mesajı göster
            sent_message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"[Resim gösterilemedi]\n\n{caption}",
                reply_markup=reply_markup
            )
            context.user_data['menu_message_id'] = sent_message.message_id
            
    except Exception as e:
        logger.error(f"Resimli menü gösterirken hata: {e}")
        # Acil durum mesajı
        try:
            sent_message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ Resimli menü gösterilirken bir hata oluştu.",
                reply_markup=reply_markup if reply_markup else None
            )
            context.user_data['menu_message_id'] = sent_message.message_id
        except Exception as final_e:
            logger.error(f"Son çare mesajını gösterirken bile hata: {final_e}")

def create_menu_keyboard(buttons, back_button=True, admin_menu=False, main_menu=True):
    """
    Standart menü klavyesi oluşturur
    
    Args:
        buttons: Liste olarak butonlar [["Buton Metni", "callback_data"], ...]
        back_button: Geri butonu eklensin mi
        admin_menu: Admin menüsüne dönüş butonu eklensin mi
        main_menu: Ana menüye dönüş butonu eklensin mi
        
    Returns:
        InlineKeyboardMarkup: Hazırlanmış klavye
    """
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    keyboard = []
    
    # Ana butonları ekle
    for button in buttons:
        if isinstance(button, list) and len(button) >= 2:
            # Tek buton
            if len(button) == 2:
                keyboard.append([InlineKeyboardButton(button[0], callback_data=button[1])])
            # Yan yana butonlar
            else:
                row = []
                for i in range(0, len(button), 2):
                    if i+1 < len(button):
                        row.append(InlineKeyboardButton(button[i], callback_data=button[i+1]))
                keyboard.append(row)
    
    # Alt butonları ekle
    bottom_buttons = []
    
    if back_button:
        if admin_menu:
            bottom_buttons.append(
                InlineKeyboardButton("🔙 Admin Menüsüne Dön", callback_data='admin_menu')
            )
        else:
            bottom_buttons.append(
                InlineKeyboardButton("🔙 Geri", callback_data='back')
            )
            
    if main_menu:
        if not bottom_buttons:
            bottom_buttons.append(
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            )
        else:
            keyboard.append(bottom_buttons)
            bottom_buttons = [InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]
            
    if bottom_buttons:
        keyboard.append(bottom_buttons)
        
    return InlineKeyboardMarkup(keyboard)