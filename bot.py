import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
from config import BOT_TOKEN, PRODUCTS_DIR, LOCATIONS_DIR, DB_NAME, ADMIN_ID
from handlers.admin.products import (
    handle_product_name,
    handle_product_description,
    handle_product_price,
    handle_product_stock,
    handle_product_image,
    handle_edit_name,
    handle_edit_description,
    handle_edit_price,
    handle_stock_input
)
from handlers.admin.categories import (
    handle_category_name,
    handle_category_description
)
from handlers.admin.wallets import handle_wallet_input
from handlers.admin.locations import handle_location_photo
from handlers import (
    # Admin handlers
    manage_products,
    manage_users,
    manage_wallets,
    start_broadcast,
    send_broadcast,
    handle_purchase_approval,
    
    # User handlers
    show_products_menu,
    view_products,
    show_cart,
    handle_add_to_cart,
    handle_cart_quantity,
    show_orders_menu,
    show_orders_by_status,
    show_order_details,
    show_payment_menu,
    show_payment_howto,
    handle_purchase_request,
    show_support_menu,
    show_faq,
    
    button_handler,
    cancel,
    
    start,
    show_main_menu,
    get_main_menu_keyboard
)
from database import Database
from states import *

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global variables
db = Database(DB_NAME)
application = None
loop = None
# Bu kodu bot.py dosyasındaki if __name__ == '__main__': bloğu içinde bot başlatma kodundan önce ekleyin:

async def start_monitoring():
    """Start monitoring tasks"""
    while True:
        try:
            available_wallets = db.get_available_wallet_count()
            total_wallets = db.get_total_wallet_count()
            
            # If less than 20% of wallets are available, notify admin
            if total_wallets > 0 and available_wallets / total_wallets < 0.2:
                await application.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"⚠️ Cüzdan Havuzu Uyarısı!\n\n"
                         f"Müsait cüzdan sayısı: {available_wallets}\n"
                         f"Toplam cüzdan sayısı: {total_wallets}\n\n"
                         f"Cüzdan havuzuna yeni cüzdanlar eklemeniz önerilir."
                )
        except Exception as e:
            logger.error(f"Error in wallet pool monitoring: {e}")
            
        # Check every 6 hours
        await asyncio.sleep(6 * 60 * 60)

async def start_locations_monitoring():
    """Location pool monitoring task"""
    while True:
        try:
            # Get all products
            products = db.get_products()
            
            for product in products:
                product_id = product[0]
                product_name = product[1]
                
                # Check available locations for this product
                available_locations = db.get_available_location_count(product_id)
                
                if available_locations < 3:  # If less than 3 locations available
                    await application.bot.send_message(
                        chat_id=ADMIN_ID,
                        text=f"⚠️ Konum Havuzu Uyarısı!\n\n"
                             f"Ürün: {product_name}\n"
                             f"Müsait konum sayısı: {available_locations}\n\n"
                             f"Bu ürün için yeni konumlar eklemeniz önerilir."
                    )
        except Exception as e:
            logger.error(f"Error in location pool monitoring: {e}")
            
        # Check every 12 hours
        await asyncio.sleep(12 * 60 * 60)

async def handle_shutdown():
    """Handle shutdown gracefully"""
    logger.info("Starting shutdown process...")
    if application:
        try:
            await shutdown(application)
            await application.stop()
            await application.shutdown()
            logger.info("Application stopped successfully")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

async def cleanup_messages(application: Application):
    """Clean up all bot messages when shutting down"""
    try:
        # Get all users from database
        users = db.get_all_users()
        
        for user_id in users:
            try:
                # Get chat history and delete bot messages
                messages = []
                async for message in application.bot.get_chat_history(user_id, limit=100):
                    if message.from_user and message.from_user.id == application.bot.id:
                        messages.append(message.message_id)
                
                # Delete messages in chunks to avoid rate limits
                for i in range(0, len(messages), 10):
                    chunk = messages[i:i + 10]
                    for msg_id in chunk:
                        try:
                            await application.bot.delete_message(chat_id=user_id, message_id=msg_id)
                        except Exception as e:
                            logger.error(f"Error deleting message {msg_id} for user {user_id}: {e}")
                    await asyncio.sleep(1)  # Small delay between chunks
                
            except Exception as e:
                logger.error(f"Error cleaning messages for user {user_id}: {e}")
                continue
                
        logger.info("Successfully cleaned up bot messages")
    except Exception as e:
        logger.error(f"Error in cleanup process: {e}")

async def shutdown(application: Application):
    """Perform cleanup when bot is shutting down"""
    logger.info("Starting cleanup process...")
    await cleanup_messages(application)
    logger.info("Cleanup completed")

if __name__ == '__main__':
    try:
        logger.info("Starting bot initialization...")

        # Ensure products directory exists
        os.makedirs(PRODUCTS_DIR, exist_ok=True)
        logger.info(f"Products directory ensured at {PRODUCTS_DIR}")
        
        # Ensure locations directory exists
        os.makedirs(LOCATIONS_DIR, exist_ok=True)
        logger.info(f"Locations directory ensured at {LOCATIONS_DIR}")

        # Initialize bot
        application = (
            Application.builder()
            .token(BOT_TOKEN)
            .connect_timeout(30.0)
            .read_timeout(30.0)
            .write_timeout(30.0)
            .pool_timeout(30.0)
            .build()
        )
        logger.info("Bot application initialized")    
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('start', start),
                CallbackQueryHandler(button_handler),
                CommandHandler('cancel', cancel)
            ],
            states={
                PRODUCT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_product_name)],
                PRODUCT_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_product_description)],
                PRODUCT_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_product_price)],
                PRODUCT_STOCK: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_product_stock)],
                PRODUCT_IMAGE: [MessageHandler(filters.PHOTO, handle_product_image)],
                EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_name)],
                EDIT_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_description)],
                EDIT_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_price)],
                CART_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_cart_quantity)],
                BROADCAST_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_broadcast)],
                WALLET_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wallet_input)],
                CATEGORY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_category_name)],
                CATEGORY_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_category_description)],
                STOCK_CHANGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_stock_input)],
                LOCATION_PHOTO: [MessageHandler(filters.PHOTO, handle_location_photo)],
            },
            fallbacks=[
                CommandHandler('cancel', cancel),
                CallbackQueryHandler(button_handler)
            ],
            per_message=False,
            per_chat=True,
            per_user=True
        )
        application.add_handler(conv_handler)
        logger.info("Handlers added to application")
        
        logger.info("Starting bot polling...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

    except KeyboardInterrupt:
        print("\nBot kapatılıyor... Lütfen bekleyin.")
        logger.info("Bot kullanıcı tarafından durduruldu")
        try:
            # Get or create event loop
            loop = asyncio.get_event_loop()
            if not loop.is_closed():
                loop.run_until_complete(handle_shutdown())
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    except Exception as e:
        logger.exception("Bot initialization failed with error:")
    finally:
        try:
            if db:
                db.close()
                logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")