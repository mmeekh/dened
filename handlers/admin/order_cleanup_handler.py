import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import Database
import sqlite3
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
db = Database('shop.db')

async def handle_cleanup_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tamamlanmış ve reddedilmiş siparişleri temizler"""
    query = update.callback_query
    await query.answer()
    
    logger.info("Sipariş temizleme işlemi başlatılıyor...")
    
    try:
        # Başlangıç mesajı gönder
        await query.message.edit_text(
            "⌛ Sipariş temizleme işlemi başlatıldı, lütfen bekleyin...",
            reply_markup=None
        )
        
        # Silinecek sipariş ID'lerini al
        order_ids = []
        db.cur.execute(
            "SELECT id FROM purchase_requests WHERE status IN ('completed', 'rejected')"
        )
        order_ids = [row[0] for row in db.cur.fetchall()]
        
        if not order_ids:
            logger.info("Temizlenecek sipariş bulunamadı.")
            await query.message.edit_text(
                "ℹ️ Temizlenecek sipariş bulunamadı.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Sipariş Yönetimi", callback_data='admin_payments')
                ]])
            )
            return
            
        logger.info(f"Toplam {len(order_ids)} sipariş temizlenecek.")
        
        # İlişkili sipariş ürünlerini temizle
        db.cur.execute(
            f"DELETE FROM purchase_request_items WHERE request_id IN ({','.join(['?'] * len(order_ids))})",
            order_ids
        )
        items_deleted = db.cur.rowcount
        logger.info(f"{items_deleted} sipariş ürünü temizlendi.")
        
        # Siparişleri temizle
        db.cur.execute(
            f"DELETE FROM purchase_requests WHERE id IN ({','.join(['?'] * len(order_ids))})",
            order_ids
        )
        orders_deleted = db.cur.rowcount
        logger.info(f"{orders_deleted} sipariş temizlendi.")
        
        # İşlemleri kaydet
        db.conn.commit()
        
        # VACUUM işlemini transaction dışında çalıştır
        # Bu kısmı düzenliyoruz
        vacuum_success = False
        try:
            # Database sınıfında connect() metodu var mı kontrol et
            if hasattr(db, 'connect'):
                logger.info("VACUUM işlemi başlatılıyor...")
                # Veritabanı bağlantısını kapat
                db_path = db.db_name
                db.conn.close()
                
                # Yeni bir bağlantı aç ve VACUUM çalıştır
                vacuum_conn = sqlite3.connect(db_path)
                vacuum_conn.execute("VACUUM")
                vacuum_conn.close()
                
                # Ana bağlantıyı yeniden aç
                db.connect()
                logger.info("Veritabanı optimize edildi.")
                vacuum_success = True
            else:
                logger.warning("Database sınıfında connect() metodu bulunamadı, VACUUM atlanıyor.")
                # Bu durumda normal bir execute ile deneyebiliriz (bu da hata verebilir)
                try:
                    db.conn.execute("PRAGMA optimize")  # VACUUM yerine daha güvenli bir alternatif
                    logger.info("Veritabanı kısmen optimize edildi (PRAGMA optimize).")
                    vacuum_success = True
                except Exception as lite_error:
                    logger.warning(f"Hafif optimizasyon da başarısız oldu: {lite_error}")
        except Exception as vac_error:
            logger.error(f"Veritabanı optimizasyonu sırasında hata: {vac_error}")
            # Bağlantının hala açık olduğundan emin ol
            try:
                # Eğer bağlantı kapalıysa ve yeniden açılabiliyorsa
                if hasattr(db, 'connect') and db.conn is None:
                    db.connect()
            except:
                logger.error("Veritabanı bağlantısı yeniden açılamadı!")
        
        # Başarılı mesajı gönder
        optimization_note = "• Veritabanı boyutu optimize edildi" if vacuum_success else "• Veritabanı optimizasyonu atlandı"
        success_message = f"""✅ Sipariş Temizleme İşlemi Tamamlandı!

🗑️ Toplam {orders_deleted} sipariş ve {items_deleted} sipariş ürünü başarıyla temizlendi.

📊 Temizlik Özeti:
• Tamamlanmış ve reddedilmiş siparişler silindi
• Bekleyen siparişler korundu
{optimization_note}

🕒 İşlem Zamanı: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"""

        await query.message.edit_text(
            success_message,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Sipariş Yönetimine Dön", callback_data='admin_payments')],
                [InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]
            ])
        )
        
    except Exception as e:
        logger.error(f"Sipariş temizleme sırasında hata: {e}")
        error_message = f"❌ Sipariş temizleme sırasında bir hata oluştu: {str(e)}"
        
        await query.message.edit_text(
            error_message,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Tekrar Dene", callback_data='confirm_cleanup_orders')],
                [InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]
            ])
        )

async def show_cleanup_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sipariş temizleme onayı göster"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Tamamlanmış ve reddedilmiş sipariş sayısını bul
        db.cur.execute(
            "SELECT COUNT(*) FROM purchase_requests WHERE status IN ('completed', 'rejected')"
        )
        completed_rejected_count = db.cur.fetchone()[0]
        
        # Toplam sipariş sayısını bul
        db.cur.execute("SELECT COUNT(*) FROM purchase_requests")
        total_count = db.cur.fetchone()[0]
        
        # Bekleyen sipariş sayısını bul
        db.cur.execute("SELECT COUNT(*) FROM purchase_requests WHERE status = 'pending'")
        pending_count = db.cur.fetchone()[0]
        
        # Veritabanı boyutunu al
        db_size = 0
        try:
            db_size = os.path.getsize('shop.db') / (1024 * 1024)  # MB cinsinden
        except:
            pass
        
        message = f"""⚠️ SİPARİŞ TEMİZLEME ONAYI

Bu işlem, tüm tamamlanmış ve reddedilmiş siparişleri kalıcı olarak silecektir.

📊 Mevcut Durum:
• Toplam Sipariş: {total_count}
• Tamamlanmış/Reddedilmiş: {completed_rejected_count}
• Bekleyen: {pending_count}
• Veritabanı Boyutu: {db_size:.2f} MB

🗑️ Temizlenecek Sipariş Sayısı: {completed_rejected_count}

⚠️ Bu işlem geri alınamaz! Devam etmek istiyor musunuz?"""
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Evet, Temizle", callback_data='cleanup_orders'),
                InlineKeyboardButton("❌ İptal", callback_data='admin_payments')
            ]
        ]
        
        await query.message.edit_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Temizleme onayı gösterilirken hata: {e}")
        await query.message.edit_text(
            "❌ Sipariş bilgileri alınırken bir hata oluştu.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')
            ]])
        )