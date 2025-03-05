import logging
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def show_generic_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                         text: str, reply_markup: InlineKeyboardMarkup = None):
    """
    Genel menü gösterici - tüm menü fonksiyonları için şablon
    Bu fonksiyon, menülerin hep aynı mesaj üzerinde kalmasını sağlar
    
    Args:
        update: Telegram update nesnesi
        context: Telegram context nesnesi
        text: Gösterilecek menü metni
        reply_markup: Klavye düğmeleri (opsiyonel)
    """
    try:
        # Mesaj ID'si saklı mı kontrol et
        menu_message_id = context.user_data.get('menu_message_id')
        
        # 1. Callback query mesajını düzenlemeyi dene (en yaygın durum)
        if update.callback_query:
            try:
                await update.callback_query.message.edit_text(
                    text=text,
                    reply_markup=reply_markup
                )
                # ID'yi güncelle
                context.user_data['menu_message_id'] = update.callback_query.message.message_id
                return
            except Exception as e:
                logger.debug(f"Callback mesajını düzenlerken hata (normal olabilir): {e}")
                # Düzenleme başarısız olursa devam et
                
        # 2. Daha önce kaydedilmiş mesaj ID'sini kullan
        if menu_message_id:
            try:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=menu_message_id,
                    text=text,
                    reply_markup=reply_markup
                )
                return
            except Exception as e:
                logger.debug(f"Kayıtlı mesajı düzenlerken hata (normal olabilir): {e}")
                # Düzenleme başarısız olursa devam et
                
        # 3. Son çare: Yeni mesaj gönder
        # Kullanıcı mesajını sil (eğer varsa)
        if update.message:
            try:
                await update.message.delete()
            except Exception as e:
                logger.debug(f"Kullanıcı mesajını silerken hata: {e}")
                
        # Yeni mesaj gönder
        sent_message = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            reply_markup=reply_markup
        )
        # Mesaj ID'sini kaydet
        context.user_data['menu_message_id'] = sent_message.message_id
        
    except Exception as e:
        logger.error(f"Menü gösterirken genel hata: {e}")
        # Ciddi hata durumunda basit bir mesaj göster
        try:
            sent_message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ Menü gösterilirken bir hata oluştu.",
                reply_markup=reply_markup if reply_markup else None
            )
            context.user_data['menu_message_id'] = sent_message.message_id
        except Exception as final_e:
            logger.error(f"Son çare mesajını gösterirken bile hata: {final_e}")

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