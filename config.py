import os
from dotenv import load_dotenv
import logging
logger = logging.getLogger(__name__)
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
BOT_PASSWORD = os.getenv('BOT_PASSWORD', 'gizli_sifre123')

if not BOT_TOKEN:
    logger.warning("BOT_TOKEN not found in environment variables. Using fallback value (NOT RECOMMENDED)")
    BOT_TOKEN = "7305637182:AAGNumHg8low_WUD3ojAl7dvHqTdmj8Hubo"  # This should be removed in production

try:
    ADMIN_ID = int(os.getenv('ADMIN_ID', '5328212723'))
except ValueError:
    logger.warning("ADMIN_ID could not be converted to integer. Using fallback value")
    ADMIN_ID = 5328212723

DB_NAME = os.getenv('DB_NAME', 'shop.db')

PRODUCTS_DIR = os.getenv('PRODUCTS_DIR', 'products')

LOCATIONS_DIR = os.getenv('LOCATIONS_DIR', 'locations')

if not all([BOT_TOKEN, ADMIN_ID]):
    logger.warning("Some essential environment variables are missing. Please check your .env file.")