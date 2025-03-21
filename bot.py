import os
import logging
import asyncio
import platform
import signal
from logging.handlers import RotatingFileHandler

from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    MessageHandler, 
    filters, 
    ConversationHandler
)
from config import BOT_TOKEN, PRODUCTS_DIR, LOCATIONS_DIR, DB_NAME, ADMIN_ID, BOT_PASSWORD
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
from handlers.menu import verify_password
from handlers.admin.wallets import handle_wallet_input
from handlers.admin.locations import handle_location_photo
from handlers.user.cart import handle_discount_code
from handlers import (
    manage_products,
    manage_users,
    manage_wallets,
    start_broadcast,
    send_broadcast,
    handle_purchase_approval,
    
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

os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,  # Use INFO level instead of DEBUG for production
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            'logs/bot.log',            # Store in logs folder
            maxBytes=10 * 1024 * 1024, # 10MB per file
            backupCount=5,             # Keep 5 backup files max (50MB total)
        ),
        logging.StreamHandler()        # Also log to console
    ]
)
logger = logging.getLogger(__name__)

logging.getLogger('telegram').setLevel(logging.WARNING)  # Telegram kütüphanesi için 
logging.getLogger('handlers.user.games').setLevel(logging.INFO)  # Oyun modülü için
logging.getLogger('handlers.admin.payments').setLevel(logging.INFO)  # Ödemeler modülü için
logging.getLogger('handlers.admin.wallets').setLevel(logging.INFO)  # Cüzdan modülü için
logging.getLogger('handlers.user.cart').setLevel(logging.INFO)  # Sepet modülü için
for handler_name in ['products', 'users', 'orders', 'payments', 'locations']:
    logging.getLogger(f'handlers.admin.{handler_name}').setLevel(logging.INFO)
    logging.getLogger(f'handlers.user.{handler_name}').setLevel(logging.INFO)


db = Database(DB_NAME)
application = None
tasks = []

async def start_monitoring():
    while True:
        try:
            available_wallets = db.get_available_wallet_count()
            total_wallets = db.get_total_wallet_count()
            
            if total_wallets > 0 and available_wallets / total_wallets < 0.2:
                await application.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"⚠️ Cüzdan Havuzu Uyarısı!\n\n"
                         f"Müsait cüzdan sayısı: {available_wallets}\n"
                         f"Toplam cüzdan sayısı: {total_wallets}\n\n"
                         f"Cüzdan havuzuna yeni cüzdanlar eklemeniz önerilir."
                )
        except asyncio.CancelledError:
            logger.info("Cüzdan monitoring görevi iptal edildi")
            return
        except Exception as e:
            logger.error(f"Error in wallet pool monitoring: {e}")
            
        try:
            await asyncio.sleep(6 * 60 * 60)
        except asyncio.CancelledError:
            logger.info("Cüzdan monitoring görevi uyku sırasında iptal edildi")
            return

async def start_locations_monitoring():
    while True:
        try:
            products = db.get_products()
            
            for product in products:
                product_id = product[0]
                product_name = product[1]
                
                available_locations = db.get_available_location_count(product_id)
                
                if available_locations < 3:
                    await application.bot.send_message(
                        chat_id=ADMIN_ID,
                        text=f"⚠️ Konum Havuzu Uyarısı!\n\n"
                             f"Ürün: {product_name}\n"
                             f"Müsait konum sayısı: {available_locations}\n\n"
                             f"Bu ürün için yeni konumlar eklemeniz önerilir."
                    )
        except asyncio.CancelledError:
            logger.info("Konum monitoring görevi iptal edildi")
            return
        except Exception as e:
            logger.error(f"Error in location pool monitoring: {e}")
        
        try:
            await asyncio.sleep(12 * 60 * 60)
        except asyncio.CancelledError:
            logger.info("Konum monitoring görevi uyku sırasında iptal edildi")
            return

async def start_game_monitoring():
    try:
        from handlers.user.games import schedule_monthly_reset
        
        game_task = asyncio.create_task(schedule_monthly_reset(application.bot))
        game_task.set_name("Game-Score-Reset")
        tasks.append(game_task)
        logger.info("Aylık oyun skoru sıfırlama görevi başlatıldı")
    except Exception as e:
        logger.error(f"Error starting game monitoring: {e}")

async def handle_shutdown():
    logger.info("Shutting down bot gracefully...")

    for task in tasks:
        if not task.done() and not task.cancelled():
            logger.info(f"Cancelling task: {task.get_name()}")
            task.cancel()
    
    if tasks:
        logger.info(f"Waiting for {len(tasks)} tasks to complete cancellation...")
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("All tasks have been properly canceled")

    if db:
        db.close()
        logger.info("Database connection closed")

    logger.info("Shutdown complete")

async def setup_signal_handlers():
    if platform.system() != 'Windows':
        loop = asyncio.get_running_loop()
        
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(
                sig,
                lambda: asyncio.create_task(shutdown(application))
            )
        logger.info("Signal handlers set up")

async def shutdown(application):
    logger.info("Starting shutdown process...")
    
    try:
        await handle_shutdown()
        
        if application:
            await application.stop()
            await application.shutdown()
            logger.info("Application stopped and shutdown completed")
            
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

if __name__ == '__main__':
    try:
        logger.info("Starting bot initialization...")

        os.makedirs(PRODUCTS_DIR, exist_ok=True)
        logger.info(f"Products directory ensured at {PRODUCTS_DIR}")
        
        os.makedirs(LOCATIONS_DIR, exist_ok=True)
        logger.info(f"Locations directory ensured at {LOCATIONS_DIR}")

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
                PASSWORD_VERIFICATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, verify_password)],
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
                DISCOUNT_CODE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_discount_code)],
                LOCATION_PHOTO: [MessageHandler(filters.PHOTO, handle_location_photo)],
                GAME_SCORE_SAVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, lambda update, context: None)],
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
        
        loop = asyncio.get_event_loop()
        asyncio.set_event_loop(loop)
        
        wallet_task = loop.create_task(start_monitoring())
        wallet_task.set_name("Wallet-Monitoring")
        tasks.append(wallet_task)
        
        location_task = loop.create_task(start_locations_monitoring())
        location_task.set_name("Location-Monitoring")
        tasks.append(location_task)
        
        game_monitoring_task = loop.create_task(start_game_monitoring())
        tasks.append(game_monitoring_task)
        
        loop.create_task(setup_signal_handlers())
        
        logger.info("Monitoring tasks started")
        logger.info("Starting bot polling...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

    except KeyboardInterrupt:
        print("\nBot kapatılıyor... Lütfen bekleyin.")
        logger.info("Bot kullanıcı tarafından durduruldu")
        try:
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