import sqlite3
import logging
from datetime import datetime, timedelta

# Logger kurulumu
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('cleanup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def cleanup_old_orders(db_name='shop.db', days=30):
    """
    Belirtilen günden eski tüm siparişleri temizler
    
    Parameters:
    db_name (str): Veritabanı dosya adı
    days (int): Kaç günden eski siparişlerin temizleneceği
    
    Returns:
    tuple: Silinen sipariş sayısı, silinen sipariş ürünleri sayısı
    """
    try:
        # Veritabanına bağlan
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        
        # Temizlenecek tarih sınırını hesapla
        cleanup_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"Temizleme işlemi başlatıldı. {cleanup_date} tarihinden eski siparişler temizlenecek.")
        
        # Silinecek sipariş ID'lerini al
        cursor.execute(
            "SELECT id FROM purchase_requests WHERE created_at < ? AND status IN ('completed', 'rejected')",
            (cleanup_date,)
        )
        order_ids = [row[0] for row in cursor.fetchall()]
        
        if not order_ids:
            logger.info("Temizlenecek sipariş bulunamadı.")
            conn.close()
            return 0, 0
            
        logger.info(f"Toplam {len(order_ids)} sipariş temizlenecek.")
        
        # İlişkili sipariş ürünlerini temizle
        cursor.execute(
            f"DELETE FROM purchase_request_items WHERE request_id IN ({','.join(['?'] * len(order_ids))})",
            order_ids
        )
        items_deleted = cursor.rowcount
        logger.info(f"{items_deleted} sipariş ürünü temizlendi.")
        
        # Siparişleri temizle
        cursor.execute(
            f"DELETE FROM purchase_requests WHERE id IN ({','.join(['?'] * len(order_ids))})",
            order_ids
        )
        orders_deleted = cursor.rowcount
        logger.info(f"{orders_deleted} sipariş temizlendi.")
        
        # İşlemleri kaydet
        conn.commit()
        
        # Veritabanı bağlantısını kapat
        conn.close()
        
        return orders_deleted, items_deleted
        
    except sqlite3.Error as e:
        logger.error(f"Veritabanı hatası: {e}")
        return 0, 0
    except Exception as e:
        logger.error(f"Hata: {e}")
        return 0, 0

def cleanup_all_completed_orders(db_name='shop.db'):
    """
    Tamamlanmış ve reddedilmiş tüm siparişleri temizler
    
    Parameters:
    db_name (str): Veritabanı dosya adı
    
    Returns:
    tuple: Silinen sipariş sayısı, silinen sipariş ürünleri sayısı
    """
    try:
        # Veritabanına bağlan
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        
        logger.info("Tamamlanmış ve reddedilmiş tüm siparişlerin temizleme işlemi başlatıldı.")
        
        # Silinecek sipariş ID'lerini al
        cursor.execute(
            "SELECT id FROM purchase_requests WHERE status IN ('completed', 'rejected')"
        )
        order_ids = [row[0] for row in cursor.fetchall()]
        
        if not order_ids:
            logger.info("Temizlenecek sipariş bulunamadı.")
            conn.close()
            return 0, 0
            
        logger.info(f"Toplam {len(order_ids)} sipariş temizlenecek.")
        
        # İlişkili sipariş ürünlerini temizle
        cursor.execute(
            f"DELETE FROM purchase_request_items WHERE request_id IN ({','.join(['?'] * len(order_ids))})",
            order_ids
        )
        items_deleted = cursor.rowcount
        logger.info(f"{items_deleted} sipariş ürünü temizlendi.")
        
        # Siparişleri temizle
        cursor.execute(
            f"DELETE FROM purchase_requests WHERE id IN ({','.join(['?'] * len(order_ids))})",
            order_ids
        )
        orders_deleted = cursor.rowcount
        logger.info(f"{orders_deleted} sipariş temizlendi.")
        
        # İşlemleri kaydet
        conn.commit()
        
        # Veritabanı bağlantısını kapat
        conn.close()
        
        return orders_deleted, items_deleted
        
    except sqlite3.Error as e:
        logger.error(f"Veritabanı hatası: {e}")
        return 0, 0
    except Exception as e:
        logger.error(f"Hata: {e}")
        return 0, 0

# Komut satırından çalıştırıldığında
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "all":
        # Tüm tamamlanmış ve reddedilmiş siparişleri temizle
        orders, items = cleanup_all_completed_orders()
        print(f"Toplam {orders} sipariş ve {items} sipariş ürünü temizlendi.")
    else:
        # Varsayılan olarak 30 günden eski siparişleri temizle
        days = 30
        if len(sys.argv) > 1:
            try:
                days = int(sys.argv[1])
            except ValueError:
                print(f"Geçersiz gün sayısı: {sys.argv[1]}. Varsayılan 30 gün kullanılıyor.")
        
        orders, items = cleanup_old_orders(days=days)
        print(f"{days} günden eski toplam {orders} sipariş ve {items} sipariş ürünü temizlendi.")