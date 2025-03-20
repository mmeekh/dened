import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import Database
from config import LOCATIONS_DIR
from states import LOCATION_PHOTO
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)
db = Database('shop.db')

async def manage_locations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show location pool management menu"""
    keyboard = [
        [
            InlineKeyboardButton("➕ Konum Ekle", callback_data='add_location'),
            InlineKeyboardButton("📋 Konumları Listele", callback_data='list_locations')
        ],
        [InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]
    ]
    
    message = """📍 Konum Havuzu Yönetimi

Konum havuzu, ürün teslimatı için kullanılan fotoğrafları yönetmenizi sağlar.
Her ürün için birden fazla konum ekleyebilirsiniz.

ℹ️ Yeni konum eklemek için "➕ Konum Ekle" butonunu kullanın."""
    
    await update.callback_query.message.edit_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def add_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start location addition process"""
    # Get list of products
    products = db.get_products()
    if not products:
        await update.callback_query.message.edit_text(
            "❌ Önce ürün eklemelisiniz!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )
        return

    keyboard = []
    for product in products:
        # Add the available location count for each product
        available_count = db.get_available_location_count(product[0])
        keyboard.append([
            InlineKeyboardButton(
                f"📦 {product[1]} ({available_count} konum)", 
                callback_data=f'select_product_location_{product[0]}'
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 Geri", callback_data='admin_locations')])
    
    await update.callback_query.message.edit_text(
        "Konum eklemek istediğiniz ürünü seçin:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_location_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Enhanced handler for location photo upload that allows multiple photos
    to be uploaded in a single session
    """
    if not update.message.photo:
        await update.message.reply_text(
            "❌ Lütfen bir fotoğraf gönderin!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 İptal", callback_data='admin_locations')
            ]])
        )
        return LOCATION_PHOTO

    product_id = context.user_data.get('selected_product_id')
    if not product_id:
        await update.message.reply_text(
            "❌ Bir hata oluştu. Lütfen tekrar deneyin.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )
        return ConversationHandler.END

    try:
        # Get product details
        product = db.get_product(product_id)
        if not product:
            await update.message.reply_text("❌ Ürün bulunamadı!")
            return ConversationHandler.END

        # Create locations directory if not exists
        locations_dir = os.path.join(LOCATIONS_DIR, str(product_id))
        os.makedirs(locations_dir, exist_ok=True)

        # Save photo
        photo = update.message.photo[-1]
        photo_file = await context.bot.get_file(photo.file_id)
        image_path = os.path.join(locations_dir, f'location_{photo.file_id}.jpg')
        await photo_file.download_to_drive(image_path)

        # Add to database
        if db.add_location(product_id, image_path):
            # Keep track of how many locations we've added in this session
            if 'locations_added' not in context.user_data:
                context.user_data['locations_added'] = 1
            else:
                context.user_data['locations_added'] += 1
                
            # Get the current count of available locations for this product
            available_count = db.get_available_location_count(product_id)
                
            # Create success message with count information
            message = f"✅ Konum #{context.user_data['locations_added']} başarıyla eklendi!\n\n"
            message += f"📦 Ürün: {product[1]}\n"
            message += f"📊 Toplam müsait konum: {available_count}\n\n"
            message += "📸 Başka bir konum fotoğrafı gönderin veya tamamlamak için butona tıklayın."
            
            # Provide buttons to complete or go back
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Tamamla", callback_data='complete_location_upload')],
                    [InlineKeyboardButton("🔙 İptal", callback_data='admin_locations')]
                ])
            )
            
            # Stay in the same state to allow uploading more photos
            return LOCATION_PHOTO
        else:
            await update.message.reply_text(
                "❌ Konum eklenirken bir hata oluştu.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Konum Havuzuna Dön", callback_data='admin_locations')
                ]])
            )
            return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error handling location photo: {e}")
        await update.message.reply_text(
            "❌ Bir hata oluştu. Lütfen tekrar deneyin.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )
    
    return ConversationHandler.END

async def complete_location_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle completion of multiple location uploads"""
    try:
        # Clear the session data
        locations_added = context.user_data.pop('locations_added', 0)
        product_id = context.user_data.pop('selected_product_id', None)
        
        if product_id:
            # Get product information
            product = db.get_product(product_id)
            product_name = product[1] if product else "Bilinmeyen ürün"
            
            # Get the current count
            available_count = db.get_available_location_count(product_id)
            
            # Create completion message
            message = f"✅ Konum ekleme tamamlandı!\n\n"
            message += f"📦 Ürün: {product_name}\n"
            message += f"📊 Eklenen konum sayısı: {locations_added}\n"
            message += f"📊 Toplam müsait konum: {available_count}"
        else:
            message = f"✅ Konum ekleme tamamlandı! {locations_added} konum eklendi."
        
        # Show completion message
        await update.callback_query.message.edit_text(
            text=message,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Konum Havuzuna Dön", callback_data='admin_locations')
            ]])
        )
        
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error completing location upload: {e}")
        await update.callback_query.message.edit_text(
            "❌ İşlem tamamlanırken bir hata oluştu.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Konum Havuzuna Dön", callback_data='admin_locations')
            ]])
        )
        return ConversationHandler.END

async def list_locations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of all locations with creation dates"""
    locations = db.get_all_locations()
    
    if not locations:
        await update.callback_query.message.edit_text(
            "❌ Henüz konum eklenmemiş.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Konum Havuzuna Dön", callback_data='admin_locations')
            ]])
        )
        return
    
    message = "📍 Konum Listesi\n\n"
    keyboard = []
    
    # Group locations by product for better organization
    from collections import defaultdict
    locations_by_product = defaultdict(list)
    
    for location in locations:
        product_id = location['product_id']
        locations_by_product[product_id].append(location)
    
    # Now show locations grouped by product
    for product_id, product_locations in locations_by_product.items():
        product = db.get_product(product_id)
        if not product:
            continue
            
        # Show product name and count
        available_count = sum(1 for loc in product_locations if not loc['is_used'])
        total_count = len(product_locations)
        
        message += f"📦 {product[1]} ({available_count}/{total_count})\n"
        message += "───────────────\n"
        
        # Show up to 5 locations per product to keep the message manageable
        for i, location in enumerate(product_locations[:5]):
            status = "🔴 Kullanıldı" if location['is_used'] else "🟢 Müsait"
            
            # Format the date from the database
            created_date = "Bilinmiyor"
            if location['created_at']:
                try:
                    # Try to parse the date string from SQLite
                    from datetime import datetime
                    if isinstance(location['created_at'], str):
                        dt = datetime.strptime(location['created_at'].split('.')[0], '%Y-%m-%d %H:%M:%S')
                        created_date = dt.strftime('%d.%m.%Y %H:%M')
                    else:
                        created_date = location['created_at'].strftime('%d.%m.%Y %H:%M')
                except Exception as e:
                    logger.error(f"Date formatting error: {e}")
            
            message += f"  {i+1}. {status} • Tarih: {created_date}\n"
            
            if not location['is_used']:
                keyboard.append([
                    InlineKeyboardButton(
                        f"❌ Sil: {product[1]} #{i+1}",
                        callback_data=f'delete_location_{location["id"]}'
                    )
                ])
        
        # If there are more locations than shown
        if len(product_locations) > 5:
            message += f"  ... ve {len(product_locations) - 5} konum daha\n"
            
        message += "\n"
    
    # Add an option to view detailed locations for specific product
    keyboard.append([InlineKeyboardButton("🔍 Ürüne Göre Filtrele", callback_data='filter_locations')])
    keyboard.append([InlineKeyboardButton("🔙 Konum Havuzuna Dön", callback_data='admin_locations')])
    
    try:
        await update.callback_query.message.edit_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error showing locations: {e}")
        # If message is too long, send a simplified version
        simplified_message = "📍 Konum Listesi\n\n"
        simplified_message += f"Toplam {len(locations)} konum bulundu.\n\n"
        simplified_message += "Konumları yönetmek için aşağıdaki butonları kullanın."
        await update.callback_query.message.edit_text(
            simplified_message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def filter_locations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show filtering options by product for locations"""
    products = db.get_products()
    
    if not products:
        await update.callback_query.message.edit_text(
            "❌ Henüz ürün bulunmamaktadır.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Konum Havuzuna Dön", callback_data='admin_locations')
            ]])
        )
        return

    keyboard = []
    for product in products:
        # Get location count for each product
        count_query = """
            SELECT COUNT(*) 
            FROM locations 
            WHERE product_id = ?
        """
        db.cur.execute(count_query, (product[0],))
        location_count = db.cur.fetchone()[0] or 0
        
        if location_count > 0:
            keyboard.append([
                InlineKeyboardButton(
                    f"📦 {product[1]} ({location_count})", 
                    callback_data=f'view_product_locations_{product[0]}'
                )
            ])
    
    keyboard.append([InlineKeyboardButton("🔙 Tüm Konumlar", callback_data='list_locations')])
    keyboard.append([InlineKeyboardButton("🔙 Konum Havuzuna Dön", callback_data='admin_locations')])
    
    await update.callback_query.message.edit_text(
        "🔍 Konumları ürüne göre filtrele:\n\nGörmek istediğiniz ürünü seçin:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def view_product_locations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all locations for a specific product"""
    product_id = int(update.callback_query.data.split('_')[3])
    
    # Get product details
    product = db.get_product(product_id)
    if not product:
        await update.callback_query.message.edit_text(
            "❌ Ürün bulunamadı!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Konum Havuzuna Dön", callback_data='admin_locations')
            ]])
        )
        return
    
    # Get all locations for this product
    query = """
        SELECT * 
        FROM locations 
        WHERE product_id = ? 
        ORDER BY is_used ASC, created_at DESC
    """
    db.cur.execute(query, (product_id,))
    locations = []
    for row in db.cur.fetchall():
        locations.append({
            'id': row[0],
            'product_id': row[1],
            'image_path': row[2],
            'is_used': row[3],
            'created_at': row[4]
        })
    
    if not locations:
        await update.callback_query.message.edit_text(
            f"❌ {product[1]} için henüz konum eklenmemiş.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ürün Filtresine Dön", callback_data='filter_locations')
            ]])
        )
        return
    
    message = f"📍 {product[1]} Konumları\n\n"
    
    # Count available and used locations
    available = sum(1 for loc in locations if not loc['is_used'])
    used = sum(1 for loc in locations if loc['is_used'])
    
    message += f"📊 Toplam: {len(locations)} konum\n"
    message += f"🟢 Müsait: {available} konum\n"
    message += f"🔴 Kullanılmış: {used} konum\n\n"
    
    keyboard = []
    
    # Show locations with details
    for i, location in enumerate(locations):
        status = "🔴 Kullanıldı" if location['is_used'] else "🟢 Müsait"
        
        # Format the date
        created_date = "Bilinmiyor"
        if location['created_at']:
            try:
                from datetime import datetime
                if isinstance(location['created_at'], str):
                    dt = datetime.strptime(location['created_at'].split('.')[0], '%Y-%m-%d %H:%M:%S')
                    created_date = dt.strftime('%d.%m.%Y %H:%M')
                else:
                    created_date = location['created_at'].strftime('%d.%m.%Y %H:%M')
            except Exception as e:
                logger.error(f"Date formatting error: {e}")
        
        message += f"{i+1}. {status} • Eklenme: {created_date}\n"
        
        # Add delete button only for unused locations
        if not location['is_used']:
            keyboard.append([
                InlineKeyboardButton(
                    f"❌ Sil: Konum #{i+1}",
                    callback_data=f'delete_location_{location["id"]}'
                )
            ])
    
    keyboard.append([InlineKeyboardButton("➕ Bu Ürüne Konum Ekle", callback_data=f'select_product_location_{product_id}')])
    keyboard.append([InlineKeyboardButton("🔙 Ürün Filtresine Dön", callback_data='filter_locations')])
    keyboard.append([InlineKeyboardButton("🔙 Konum Havuzuna Dön", callback_data='admin_locations')])
    
    try:
        await update.callback_query.message.edit_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error showing product locations: {e}")
        # If message is too long, send a simplified version
        simplified_message = f"📍 {product[1]} Konumları\n\n"
        simplified_message += f"Toplam {len(locations)} konum bulundu.\n"
        simplified_message += f"Müsait: {available}, Kullanılmış: {used}\n\n"
        simplified_message += "Metin çok uzun olduğu için detaylar gösterilemiyor."
        
        await update.callback_query.message.edit_text(
            simplified_message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )