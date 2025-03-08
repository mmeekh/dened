import os
import logging
import asyncio
import platform
import signal
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
from handlers.user.cart import handle_discount_code
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

# Logging yapılandırması
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global değişkenler
db = Database(DB_NAME)
application = None
tasks = []  # Tüm oluşturulan görevleri bu listede saklayacağız

# Monitoring görevleri
async def start_monitoring():
    """Cüzdan havuzu monitoring görevi"""
    while True:
        try:
            available_wallets = db.get_available_wallet_count()
            total_wallets = db.get_total_wallet_count()
            
            # Eğer müsait cüzdanlar toplam cüzdanların %20'sinden azsa admin'e bildir
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
            return  # Görev iptal edildiğinde temiz çıkış
        except Exception as e:
            logger.error(f"Error in wallet pool monitoring: {e}")
            
        try:
            # 6 saatte bir kontrol et
            await asyncio.sleep(6 * 60 * 60)
        except asyncio.CancelledError:
            logger.info("Cüzdan monitoring görevi uyku sırasında iptal edildi")
            return  # Uyku sırasında iptal edilirse temiz çıkış

async def start_locations_monitoring():
    """Konum havuzu monitoring görevi"""
    while True:
        try:
            # Tüm ürünleri al
            products = db.get_products()
            
            for product in products:
                product_id = product[0]
                product_name = product[1]
                
                # Bu ürün için müsait konum sayısını kontrol et
                available_locations = db.get_available_location_count(product_id)
                
                if available_locations < 3:  # 3'ten az konum kaldıysa uyarı ver
                    await application.bot.send_message(
                        chat_id=ADMIN_ID,
                        text=f"⚠️ Konum Havuzu Uyarısı!\n\n"
                             f"Ürün: {product_name}\n"
                             f"Müsait konum sayısı: {available_locations}\n\n"
                             f"Bu ürün için yeni konumlar eklemeniz önerilir."
                    )
        except asyncio.CancelledError:
            logger.info("Konum monitoring görevi iptal edildi")
            return  # Görev iptal edildiğinde temiz çıkış
        except Exception as e:
            logger.error(f"Error in location pool monitoring: {e}")
        
        try:
            # 12 saatte bir kontrol et
            await asyncio.sleep(12 * 60 * 60)
        except asyncio.CancelledError:
            logger.info("Konum monitoring görevi uyku sırasında iptal edildi")
            return  # Uyku sırasında iptal edilirse temiz çıkış

async def start_game_monitoring():
    """Oyun puanlarının aylık sıfırlanmasını takip et"""
    from handlers.user.games import schedule_monthly_reset
    
    # Aylık sıfırlama zamanını takip edecek görevi başlat
    game_task = asyncio.create_task(schedule_monthly_reset(application.bot))
    tasks.append(game_task)  # Görevi listeye ekle
    logger.info("Aylık oyun skoru sıfırlama görevi başlatıldı")

# Kapatma ve temizleme fonksiyonları
async def handle_shutdown():
    """Handles cleanup tasks during shutdown"""
    logger.info("Shutting down bot...")

    # Cancel all running tasks
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    
    logger.info(f"Cancelled {len(tasks)} pending tasks")

    # Wait for all tasks to finish
    try:
        await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        logger.error(f"Error while shutting down tasks: {e}")

    logger.info("Shutdown complete")


async def cleanup_messages(application: Application):
    """Bot kapatılırken tüm mesajları temizle"""
    try:
        # Tüm kullanıcıları veritabanından al
        users = db.get_all_users()
        
        for user_id in users:
            try:
                # Sohbet geçmişini al ve bot mesajlarını sil
                messages = []
                async for message in application.bot.get_chat_history(user_id, limit=100):
                    if message.from_user and message.from_user.id == application.bot.id:
                        messages.append(message.message_id)
                
                # Mesajları daha küçük parçalar halinde sil (rate limitleri aşmamak için)
                for i in range(0, len(messages), 10):
                    chunk = messages[i:i + 10]
                    for msg_id in chunk:
                        try:
                            await application.bot.delete_message(chat_id=user_id, message_id=msg_id)
                        except Exception as e:
                            logger.error(f"Error deleting message {msg_id} for user {user_id}: {e}")
                    await asyncio.sleep(1)  # Parçalar arasında küçük bir gecikme
                
            except Exception as e:
                logger.error(f"Error cleaning messages for user {user_id}: {e}")
                continue
                
        logger.info("Successfully cleaned up bot messages")
    except Exception as e:
        logger.error(f"Error in cleanup process: {e}")

async def shutdown(application: Application):
    """Perform cleanup operations when shutting down the bot."""
    logger.info("Starting cleanup process...")

    try:
        # Clean up messages before shutting down
        await cleanup_messages(application)
        logger.info("Message cleanup completed successfully.")

        # Stop the application
        await application.stop()
        logger.info("Application stopped successfully.")

        # Perform additional cleanup if necessary
        await application.shutdown()
        logger.info("Application shutdown completed.")

    except Exception as e:
        logger.error(f"Error during shutdown process: {e}")


# Ana program
if __name__ == '__main__':
    try:
        logger.info("Starting bot initialization...")

        # Ürünler dizininin varlığını kontrol et
        os.makedirs(PRODUCTS_DIR, exist_ok=True)
        logger.info(f"Products directory ensured at {PRODUCTS_DIR}")
        
        # Konumlar dizininin varlığını kontrol et
        os.makedirs(LOCATIONS_DIR, exist_ok=True)
        logger.info(f"Locations directory ensured at {LOCATIONS_DIR}")

        # Bot'u başlat
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
        
        # Conversation handler tanımlama
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
        
        # Event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Monitoring görevlerini başlat
        wallet_task = loop.create_task(start_monitoring())
        tasks.append(wallet_task)
        
        location_task = loop.create_task(start_locations_monitoring())
        tasks.append(location_task)
        
        game_monitoring_task = loop.create_task(start_game_monitoring())
        tasks.append(game_monitoring_task)
        
        logger.info("Monitoring tasks started")
        
        # Bot'un çalışmasını başlat
        logger.info("Starting bot polling...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

    except KeyboardInterrupt:
        print("\nBot kapatılıyor... Lütfen bekleyin.")
        logger.info("Bot kullanıcı tarafından durduruldu")
        try:
            # Event loop'u al veya oluştur
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