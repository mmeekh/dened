import os
import sys
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()
loaded = load_dotenv()
if not loaded:
    print("HATA: .env dosyası bulunamadı!")
    print("Lütfen .env.example dosyasını .env olarak kopyalayıp değerleri ayarlayın")
    sys.exit(1)

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    print("HATA: BOT_TOKEN environment variable gerekli!")
    sys.exit(1)
try:
    ADMIN_ID = int(os.getenv('ADMIN_ID'))
    if not ADMIN_ID:
        logger.critical("ADMIN_ID environment variable is required!")
        sys.exit(1)
except (TypeError, ValueError):
    logger.critical("ADMIN_ID must be a valid integer!")
    sys.exit(1)

BOT_PASSWORD = os.getenv('BOT_PASSWORD')
if not BOT_PASSWORD:
    logger.critical("BOT_PASSWORD environment variable is required!")
    sys.exit(1)

DB_NAME = os.getenv('DB_NAME', 'shop.db')
PRODUCTS_DIR = os.getenv('PRODUCTS_DIR', 'products')
LOCATIONS_DIR = os.getenv('LOCATIONS_DIR', 'locations')

logger.info(f"Configuration loaded:")
logger.info(f"- Admin ID: {ADMIN_ID}")
logger.info(f"- Database: {DB_NAME}")
logger.info(f"- Products directory: {PRODUCTS_DIR}")
logger.info(f"- Locations directory: {LOCATIONS_DIR}")