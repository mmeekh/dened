import logging
import importlib  # Bu satırı ekleyin
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config import ADMIN_ID
from states import *
from database import Database
from .menu import show_main_menu, get_main_menu_keyboard
from .admin import (
    manage_products,
    add_product,
    show_edit_menu,
    handle_delete_product,
    manage_users,
    manage_wallets,
    add_wallet,
    list_wallets,
    manage_locations,
    add_location,
    list_locations,
    add_wallet,
    list_wallets,
    manage_categories,
    add_category,
    delete_category,
    show_stats_menu, show_general_stats, show_sales_stats,
    show_user_stats, show_performance_stats,
    start_broadcast,
    handle_purchase_approval,
    show_pending_purchases
)
from .user import (
    show_products_menu,
    view_products,
    show_cart,
    handle_add_to_cart,
    show_orders_menu,
    show_orders_by_status,
    show_order_details,
    show_payment_menu,
    show_payment_howto,
    check_payment_status,
    show_qr_code,
    handle_purchase_request,
    show_support_menu,
    show_faq
)

logger = logging.getLogger(__name__)
db = Database('shop.db')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()

    try:
        if query.data != 'exit' and db.is_user_banned(update.effective_user.id):
            try:
                await query.message.delete()
            except Exception as e:
                logger.error(f"Error deleting message: {e}")
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⛔️ Hesabınız yasaklanmıştır. Daha fazla işlem yapamazsınız.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Çıkış", callback_data='exit')
                ]])
            )
            return ConversationHandler.END
    
        if query.data == 'main_menu':
            await show_main_menu(update, context)
            return ConversationHandler.END
        elif query.data == 'exit':
            await query.message.edit_text("👋 Görüşmek üzere!")
            return ConversationHandler.END
        
        # Admin handlers
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
        elif query.data.startswith('delete_product_'):
            product_id = int(query.data.split('_')[2])
            await handle_delete_product(update, context, product_id)
            return
        elif query.data == 'edit_name':
            await query.message.edit_text(
                "Yeni ürün adını girin:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 İptal", callback_data='admin_products')
                ]])
            )
            return EDIT_NAME
        elif query.data == 'edit_description':
            await query.message.edit_text(
                "Yeni ürün açıklamasını girin:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 İptal", callback_data='admin_products')
                ]])
            )
            return EDIT_DESCRIPTION
        elif query.data == 'edit_price':
            await query.message.edit_text(
                "Yeni ürün fiyatını USDT olarak girin (sadece sayı):",
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
                await query.message.edit_text(
                    "✅ Cüzdan başarıyla silindi!",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Cüzdan Havuzuna Dön", callback_data='admin_wallets')
                    ]])
                )
            else:
                await query.message.edit_text(
                    "❌ Cüzdan silinirken bir hata oluştu.",
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
        elif query.data == 'add_location':
            await add_location(update, context)
            return
        elif query.data == 'list_locations':
            await list_locations(update, context)
            return
        elif query.data.startswith('select_product_location_'):
            product_id = int(query.data.split('_')[3])
            context.user_data['selected_product_id'] = product_id
            await query.message.edit_text(
                "📸 Lütfen konum fotoğrafını gönderin:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 İptal", callback_data='admin_locations')
                ]])
            )
            return LOCATION_PHOTO
        elif query.data.startswith('delete_location_'):
            location_id = int(query.data.split('_')[2])
            if db.delete_location(location_id):
                await query.message.edit_text(
                    "✅ Konum başarıyla silindi!",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Konum Havuzuna Dön", callback_data='admin_locations')
                    ]])
                )
            else:
                await query.message.edit_text(
                    "❌ Konum silinirken bir hata oluştu.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Konum Havuzuna Dön", callback_data='admin_locations')
                    ]])
                )
            return
        elif query.data == 'show_wallet':
            # Alternatif bir işlem yapın, örneğin ödeme menüsüne yönlendirin
            user_payments = importlib.import_module('.user.payments', package='handlers')
            await user_payments.show_payment_menu(update, context)
            return
        # User handlers
        elif query.data == 'products_menu':
            await show_products_menu(update, context)
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
        elif query.data == 'check_payment_status':
            await check_payment_status(update, context)
            return
        elif query.data == 'show_qr_code':
            await show_qr_code(update, context)
            return
        elif query.data == 'request_purchase':
            try:
                user_payments = importlib.import_module('.user.payments', package='handlers')
                logger.info("Handling purchase request")
                await user_payments.handle_purchase_request(update, context)
            except Exception as e:
                logger.error(f"Error in request_purchase handler: {e}")
                await query.message.edit_text(
                    "Ödeme işlemi sırasında bir hata oluştu. Lütfen tekrar deneyin.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Sepete Dön", callback_data='show_cart')
                    ]])
                )
            return
        elif query.data == 'support_menu':  
            await show_support_menu(update, context)
            return
        elif query.data == 'create_ticket':
            await query.message.edit_text(
                text="Lütfen destek talebinizi yazın:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 İptal", callback_data='support_menu')]
                ])
            )
            return SUPPORT_TICKET
        elif query.data == 'faq':
            await show_faq(update, context)
            return

    except Exception as e:
        logger.error(f"Error in button_handler: {e}")
        await query.message.edit_text(
            "Bir hata oluştu. Lütfen tekrar deneyin.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current operation and return to main menu"""
    try:
        await update.message.reply_text('İşlem iptal edildi.')
        await show_main_menu(update, context)
    except Exception as e:
        logger.error(f"Error in cancel command: {e}")
        await update.message.reply_text(
            'İşlem iptal edildi.',
            reply_markup=get_main_menu_keyboard(update.effective_user.id)
        )
    return ConversationHandler.END