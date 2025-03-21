import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config import ADMIN_ID
from states import *
from database import Database
from .menu import show_main_menu
from utils.menu_utils import show_generic_menu
from .admin.order_cleanup_handler import show_cleanup_confirmation, handle_cleanup_orders
from .admin.payments import show_admin_orders_by_status
from .admin.locations import (
    complete_location_upload,
    filter_locations,
    view_product_locations
)
from .user.games import (
    show_games_menu, 
    play_flappy_weed, 
    start_flappy_game, 
    show_leaderboard, 
    handle_game_score, 
    claim_rewards, 
    confirm_reward
)
from .user.coupons import show_my_coupons

from .admin import (
    manage_products,
    manage_users,
    manage_wallets,
    add_wallet,
    list_wallets,
    manage_locations,
    add_location,
    list_locations,
    manage_categories,
    add_category,
    delete_category,
    show_stats_menu, 
    show_sales_stats,
    show_general_stats,
    show_user_stats, 
    show_performance_stats,
    start_broadcast,
    handle_purchase_approval,
    release_all_wallets,
    show_pending_purchases
)
from .admin.products import (
    add_product,
    show_edit_menu,
    handle_delete_product,
    edit_stock
)

from .user import (
    view_products,
    show_cart,
    handle_add_to_cart,
    show_orders_menu,
    show_orders_by_status,
    show_order_details,
    show_payment_menu,
    show_payment_howto,
    show_qr_code,
    show_support_menu,
    show_faq
)
from .user.cart import (
    show_cart,
    handle_add_to_cart,
    handle_cart_quantity,
    prompt_discount_code, 
    show_user_coupons,
    apply_coupon_from_list
)
logger = logging.getLogger(__name__)
db = Database('shop.db')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Tüm buton etkileşimlerini yönetir.
    Kaydırma problemini önlemek için mesajları silmek yerine düzenler.
    """
    query = update.callback_query
    await query.answer()  # Butona tıklandığını onayla
    try:
        if query.data == 'retry_password':
            try:
                await query.message.edit_text(
                    "🔐 Lütfen erişim şifresini girin:",
                    reply_markup=None
                )
                context.user_data['password_message_id'] = query.message.message_id
            except Exception as e:
                # If editing fails (likely due to identical content), delete and send new
                try:
                    await query.message.delete()
                except Exception as del_e:
                    logger.debug(f"Could not delete message: {del_e}")
                    
                sent_message = await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="🔐 Lütfen erişim şifresini girin:",
                    reply_markup=None
                )
                context.user_data['password_message_id'] = sent_message.message_id
            
            return PASSWORD_VERIFICATION
            
        # Admin kullanıcısı için şifre doğrulamasını atlayın
        if update.effective_user.id == ADMIN_ID:
            # Admin kullanıcı için şifre doğrulaması gerekmez
            pass
        elif query.data != 'exit' and not db.is_user_authorized(update.effective_user.id):
            error_message = "🔐 Bu özel servis sadece yetkili kişiler içindir. Lütfen erişim şifresini girin:"
            
            try:
                # Clear existing message and prompt for password
                await query.message.edit_text(
                    text=error_message,
                    reply_markup=None
                )
                context.user_data['password_message_id'] = query.message.message_id
            except Exception as e:
                logger.debug(f"Could not edit message: {e}")
                try:
                    await query.message.delete()
                except Exception as del_e:
                    logger.debug(f"Could not delete message: {del_e}")
                    
                sent_message = await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=error_message,
                    reply_markup=None
                )
                context.user_data['password_message_id'] = sent_message.message_id
                
            return PASSWORD_VERIFICATION
        
        if query.data != 'exit' and db.is_user_banned(update.effective_user.id):
            error_message = "⛔️ Hesabınız yasaklanmıştır. Daha fazla işlem yapamazsınız."
            
            # Mevcut mesajı düzenle
            await show_generic_menu(
                update=update,
                context=context,
                text=error_message,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Çıkış", callback_data='exit')
                ]])
            )
            return ConversationHandler.END
    
        # Ana menüye dön
        if query.data == 'main_menu':
            await force_delete_previous_messages(update, context, context.bot)
            await show_main_menu(update, context)
            return
        elif query.data == 'release_all_wallets':
            await release_all_wallets(update, context)
            return
        # Çıkış yap
        elif query.data == 'exit':
            await show_generic_menu(
                update=update,
                context=context,
                text="👋 Görüşmek üzere!",
                reply_markup=None
            )
            return ConversationHandler.END
            
        # Kuponlar sayfası
        elif query.data == 'my_coupons':
            await show_my_coupons(update, context)
            return
        # Siparişleri temizleme işlemleri
        elif query.data == 'confirm_cleanup_orders':
            await show_cleanup_confirmation(update, context)
            return
        elif query.data == 'cleanup_orders':
            await handle_cleanup_orders(update, context)
            return
        elif query.data == 'prompt_discount_code':
            await prompt_discount_code(update, context)
        # Admin handler işlemleri
        elif query.data == 'admin_pending_orders':
            await show_admin_orders_by_status(update, context, 'pending')
            return
        elif query.data == 'admin_completed_orders':
            await show_admin_orders_by_status(update, context, 'completed')
            return
        elif query.data == 'admin_rejected_orders':
            await show_admin_orders_by_status(update, context, 'rejected')
            return
        elif query.data == 'admin_products':
            await manage_products(update, context)
            return
        elif query.data == 'add_product':
            return await add_product(update, context)
        elif query.data.startswith('edit_product_'):
            product_id = int(query.data.split('_')[2])
            context.user_data['edit_product_id'] = product_id
            await show_edit_menu(update, context, product_id)
            return
        elif query.data == 'edit_stock':
            await edit_stock(update, context)
            return STOCK_CHANGE
        elif query.data.startswith('delete_product_'):
            product_id = int(query.data.split('_')[2])
            await handle_delete_product(update, context, product_id)
            return
        elif query.data == 'edit_name':
            await show_generic_menu(
                update=update,
                context=context,
                text="Yeni ürün adını girin:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 İptal", callback_data='admin_products')
                ]])
            )
            return EDIT_NAME
        elif query.data == 'edit_description':
            await show_generic_menu(
                update=update,
                context=context,
                text="Yeni ürün açıklamasını girin:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 İptal", callback_data='admin_products')
                ]])
            )
            return EDIT_DESCRIPTION
        elif query.data == 'edit_price':
            await show_generic_menu(
                update=update,
                context=context,
                text="Yeni ürün fiyatını USDT olarak girin (sadece sayı):",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 İptal", callback_data='admin_products')
                ]])
            )
            return EDIT_PRICE
        elif query.data == 'admin_users':
            await manage_users(update, context)
            return
        elif query.data == 'admin_wallets':
            await manage_wallets(update, context)
            return
        elif query.data == 'add_wallet':
            await add_wallet(update, context)
            return WALLET_INPUT
        elif query.data == 'list_wallets':
            await list_wallets(update, context)
            return
        elif query.data.startswith('delete_wallet_'):
            wallet_id = int(query.data.split('_')[2])
            if db.delete_wallet(wallet_id):
                await show_generic_menu(
                    update=update,
                    context=context,
                    text="✅ Cüzdan başarıyla silindi!",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Cüzdan Havuzuna Dön", callback_data='admin_wallets')
                    ]])
                )
            else:
                await show_generic_menu(
                    update=update,
                    context=context,
                    text="❌ Cüzdan silinirken bir hata oluştu.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Cüzdan Havuzuna Dön", callback_data='admin_wallets')
                    ]])
                )
            return
        elif query.data == 'stats_menu':
            await show_stats_menu(update, context)
            return
        elif query.data == 'general_stats':
            await show_general_stats(update, context)
            return
        elif query.data == 'sales_stats':
            await show_sales_stats(update, context)
            return
        elif query.data == 'user_stats':
            await show_user_stats(update, context)
            return
        elif query.data == 'performance_stats':
            await show_performance_stats(update, context)
            return
        elif query.data == 'manage_categories':
            await manage_categories(update, context)
            return
        elif query.data == 'add_category':
            await add_category(update, context)
            return CATEGORY_NAME
        elif query.data.startswith('delete_category_'):
            await delete_category(update, context)
            return
        elif query.data == 'admin_payments':
            await show_pending_purchases(update, context)
            return
        elif query.data == 'send_broadcast':
            await start_broadcast(update, context)
            return BROADCAST_MESSAGE
        elif query.data.startswith(('approve_purchase_', 'reject_purchase_')):
            await handle_purchase_approval(update, context)
            return
        elif query.data == 'admin_locations':
            await manage_locations(update, context)
            return
        elif query.data == 'filter_locations':
            await filter_locations(update, context)
            return

        elif query.data.startswith('view_product_locations_'):
            await view_product_locations(update, context)
            return
        elif query.data == 'complete_location_upload':
            await complete_location_upload(update, context)
            return ConversationHandler.END
        elif query.data == 'add_location':
            await add_location(update, context)
            return
        elif query.data == 'list_locations':
            await list_locations(update, context)
            return
        elif query.data.startswith('select_product_location_'):
            product_id = int(query.data.split('_')[3])
            context.user_data['selected_product_id'] = product_id
            context.user_data['locations_added'] = 0
            product = db.get_product(product_id)
            product_name = product[1] if product else "Ürün"
            
            await query.message.edit_text(
                text=f"📸 {product_name} için konum fotoğrafı gönderin:\n\n"
                    f"⚠️ Birden fazla fotoğraf gönderebilirsiniz. Her gönderi sonrası tamamlamak için 'Tamamla' butonuna tıklayabilirsiniz.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 İptal", callback_data='admin_locations')
                ]])
            )
            return LOCATION_PHOTO
        elif query.data.startswith('delete_location_'):
            location_id = int(query.data.split('_')[2])
            if db.delete_location(location_id):
                await show_generic_menu(
                    update=update,
                    context=context,
                    text="✅ Konum başarıyla silindi!",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Konum Havuzuna Dön", callback_data='admin_locations')
                    ]])
                )
            else:
                await show_generic_menu(
                    update=update,
                    context=context,
                    text="❌ Konum silinirken bir hata oluştu.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Konum Havuzuna Dön", callback_data='admin_locations')
                    ]])
                )
            return
        elif query.data == 'view_all_orders':
            import importlib
            admin_payments = importlib.import_module('.admin.payments', package='handlers')
            await admin_payments.view_all_orders(update, context)
            return
        
        # Game handlers - YENİ EKLENEN ÖDÜL SİSTEMİ KODLARI
        elif query.data == 'games_menu':
            await show_games_menu(update, context)
            return
        elif query.data == 'play_flappy_weed':
            await play_flappy_weed(update, context)
            return
        elif query.data.startswith('start_flappy_'):
            await start_flappy_game(update, context)
            return
        elif query.data == 'show_leaderboard':
            await show_leaderboard(update, context)
            return
        elif query.data.startswith('save_score_'):
            await handle_game_score(update, context)
            return
        # Yeni eklenen ödül talep sistemi
        elif query.data == 'claim_rewards':
            await claim_rewards(update, context)
            return
        elif query.data.startswith('confirm_reward_'):
            await confirm_reward(update, context)
            return
            
        # User handler işlemleri
        elif query.data == 'products_menu':
            await view_products(update, context)
            return
        elif query.data == 'view_products':
            await view_products(update, context)
            return
        elif query.data == 'show_cart':
            await show_cart(update, context)
            return
        elif query.data.startswith('add_to_cart_'):
            await handle_add_to_cart(update, context)
            return CART_QUANTITY
        elif query.data == 'orders_menu':
            await show_orders_menu(update, context)
            return
        elif query.data.startswith('view_order_'):
            order_id = int(query.data.split('_')[2])
            await show_order_details(update, context, order_id)
            return
        elif query.data == 'pending_orders':
            await show_orders_by_status(update, context, 'pending')
            return
        elif query.data == 'completed_orders':
            await show_orders_by_status(update, context, 'completed')
            return
        elif query.data == 'rejected_orders':
            await show_orders_by_status(update, context, 'rejected')
            return
        elif query.data == 'payment_menu':
            await show_payment_menu(update, context)
            return
        elif query.data == 'payment_howto':
            await show_payment_howto(update, context)
            return
        elif query.data == 'show_qr_code':
            await show_qr_code(update, context)
            return
        elif query.data == 'show_wallet':
            import importlib
            user_payments = importlib.import_module('.user.payments', package='handlers')
            await user_payments.show_wallet_address(update, context)
            return
        elif query.data == 'request_purchase':
            try:
                import importlib
                user_payments = importlib.import_module('.user.payments', package='handlers')
                logger.info("Handling purchase request")
                await user_payments.handle_purchase_request(update, context)
            except Exception as e:
                logger.error(f"Error in request_purchase handler: {e}")
                await show_generic_menu(
                    update=update,
                    context=context,
                    text="Ödeme işlemi sırasında bir hata oluştu. Lütfen tekrar deneyin.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Sepete Dön", callback_data='show_cart')
                    ]])
                )
            return
        elif query.data == 'support_menu':
            await show_support_menu(update, context)
            return
        elif query.data == 'faq':
            await show_faq(update, context)
            return
        elif query.data.startswith('toggle_ban_'):
            user_id = int(query.data.split('_')[2])
            if db.toggle_user_ban(user_id):
                user_stats = db.get_user_stats(user_id)
                if user_stats:
                    is_banned = user_stats[5]
                    status = "yasaklandı" if is_banned else "yasağı kaldırıldı"                    
                    try:
                        message = "⛔️ Hesabınız yasaklanmıştır." if is_banned else "✅ Hesabınızın yasağı kaldırılmıştır."
                        keyboard = [[InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]]
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=message,
                            reply_markup=InlineKeyboardMarkup(keyboard)
                        )
                    except Exception as e:
                        logger.error(f"Error notifying user {user_id}: {e}")
                    
                    await query.answer(f"Kullanıcı başarıyla {status}!")
                    await show_generic_menu(
                        update=update,
                        context=context,
                        text=f"✅ Kullanıcı #{user_id} {status}!",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("🔙 Kullanıcılara Dön", callback_data='admin_users')
                        ]])
                    )
                else:
                    await query.answer("Kullanıcı bulunamadı!")
            else:
                await query.answer("İşlem başarısız oldu!")
                # Kullanıcı listesine geri dön
                await manage_users(update, context)
            return
        elif query.data.startswith('remove_cart_'):
            try:
                cart_id = int(query.data.split('_')[2])
                logger.info(f"Removing cart item with ID: {cart_id}")
                success = db.remove_from_cart(cart_id)
                if success:
                    logger.info(f"Successfully removed cart item {cart_id}")
                else:
                    logger.warning(f"Failed to remove cart item {cart_id}")
                # Refresh the cart view
                await show_cart(update, context)
            except Exception as e:
                logger.error(f"Error processing cart removal: {e}")
                await update.callback_query.answer("Ürün sepetten kaldırılırken bir hata oluştu")
            return
        elif query.data == 'show_my_coupons':
            await show_user_coupons(update, context)
            return
        elif query.data.startswith('use_coupon_'):
            await apply_coupon_from_list(update, context)
            return
        elif query.data == 'remove_discount':
            try:
                from handlers.user.cart import remove_discount
                await remove_discount(update, context)
            except ImportError:
                # If not imported, define a simple inline version
                if 'active_discount' in context.user_data:
                    del context.user_data['active_discount']
                await query.answer("✅ İndirim kaldırıldı", show_alert=True)
                await show_cart(update, context)
            return

    except Exception as e:
        logger.error(f"Error in button_handler: {e}")
        await show_generic_menu(
            update=update,
            context=context,
            text="Bir hata oluştu. Lütfen tekrar deneyin.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """İşlemi iptal et ve ana menüye dön"""
    try:
        await update.message.reply_text('İşlem iptal edildi.')
        await show_main_menu(update, context)
    except Exception as e:
        logger.error(f"Error in cancel command: {e}")
        from .menu import get_main_menu_keyboard
        await show_generic_menu(
            update=update,
            context=context,
            text='İşlem iptal edildi.',
            reply_markup=get_main_menu_keyboard(update.effective_user.id)
        )
    return ConversationHandler.END
async def force_delete_previous_messages(update, context, bot):
    """
    Forces deletion of previous messages to keep UI clean
    """
    user_id = update.effective_chat.id
    # List of all possible message ID keys we might be tracking
    message_keys = [
        'menu_message_id', 
        'last_payment_message', 
        'last_bot_message_id',
        'current_message_id',
        'payment_prev_message_id'
    ]
    
    # Try to delete any tracked messages
    for key in message_keys:
        if key in context.user_data:
            message_id = context.user_data[key]
            try:
                await bot.delete_message(chat_id=user_id, message_id=message_id)
                del context.user_data[key]  # Remove the reference
            except Exception as e:
                pass  # Ignore errors, just continue
    
    # Also try to delete current message if it's a callback
    if update.callback_query and update.callback_query.message:
        try:
            await update.callback_query.message.delete()
        except Exception as e:
            pass 