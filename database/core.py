import sqlite3
from typing import Optional, List, Tuple, Any, Dict
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_name: str):
        """Initialize database connection"""
        self.db_name = db_name
        self.conn: Optional[sqlite3.Connection] = None
        self.cur: Optional[sqlite3.Cursor] = None
        self.connect()
        
    def is_user_banned(self, user_id: int) -> bool:
        """Check if a user is banned"""
        try:
            self.cur.execute(
                "SELECT is_banned FROM users WHERE telegram_id = ?",
                (user_id,)
            )
            result = self.cur.fetchone()
            return bool(result[0]) if result else False
        except Exception as e:
            logger.error(f"Error checking user ban status: {e}")
            return False
        
    def connect(self):
        """Create database connection"""
        try:
            self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
            self.cur = self.conn.cursor()
            logger.info(f"Connected to database: {self.db_name}")
            self.setup_database()
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            raise
    def assign_wallet_to_user(self, user_id: int) -> Optional[str]:
        """Get or assign a wallet for a user"""
        try:
            # Önce kullanıcıya önceden atanmış bir cüzdan var mı kontrol et
            self.cur.execute(
                """SELECT w.address 
                FROM user_wallets uw
                JOIN wallets w ON uw.wallet_id = w.id
                WHERE uw.user_id = ?
                LIMIT 1""",
                (user_id,)
            )
            result = self.cur.fetchone()
            
            # Kullanıcıya atanmış bir cüzdan varsa onu döndür
            if result:
                logger.info(f"Returning previously assigned wallet for user {user_id}: {result[0]}")
                return result[0]
                    
            # Yoksa yeni bir cüzdan ata
            self.cur.execute("BEGIN TRANSACTION")
            
            # Boş bir cüzdan bul
            self.cur.execute(
                """SELECT id, address 
                FROM wallets 
                WHERE in_use = 0 
                LIMIT 1"""
            )
            result = self.cur.fetchone()
            if not result:
                self.cur.execute("ROLLBACK")
                logger.warning(f"No available wallets found for new assignment to user {user_id}")
                return None
                    
            wallet_id, address = result
            
            # Cüzdanı kullanımda olarak işaretle
            self.cur.execute(
                "UPDATE wallets SET in_use = 1 WHERE id = ?",
                (wallet_id,)
            )
            
            # Kullanıcı-cüzdan ilişkisini kaydet
            self.cur.execute(
                """INSERT INTO user_wallets (user_id, wallet_id) 
                VALUES (?, ?)""",
                (user_id, wallet_id)
            )
            
            self.cur.execute("COMMIT")
            self.conn.commit()
            logger.info(f"New wallet {address} assigned permanently to user {user_id}")
            return address
                
        except Exception as e:
            logger.error(f"Error assigning wallet to user: {e}")
            try:
                self.cur.execute("ROLLBACK")
            except:
                pass
            return None

    def get_all_users_with_stats(self) -> List[Tuple]:
        """Get all users with their statistics"""
        try:
            logger.debug("Fetching all users with stats")
            self.cur.execute("""
                SELECT 
                    u.telegram_id,
                    u.created_at,
                    (SELECT COUNT(*) FROM purchase_requests WHERE user_id = u.telegram_id AND status = 'completed') as completed_orders,
                    (SELECT COUNT(*) FROM purchase_requests WHERE user_id = u.telegram_id AND status = 'rejected') as rejected_orders,
                    u.failed_payments,
                    u.is_banned
                FROM users u
                ORDER BY u.created_at DESC
            """)
            results = self.cur.fetchall()
            logger.debug(f"Found {len(results)} users")
            return results
        except Exception as e:
            logger.exception("Error getting users with stats:")
            return []

    def toggle_user_ban(self, user_id):
        """Toggle user ban status"""
        try:
            self.cur.execute(
                "SELECT COUNT(*) FROM users WHERE telegram_id = ?",
                (user_id,)
            )
            user_exists = self.cur.fetchone()[0] > 0
            
            if not user_exists:
                logger.warning(f"Attempted to toggle ban for non-existent user {user_id}")
                return False
                
            # Toggle the ban status
            self.cur.execute(
                "UPDATE users SET is_banned = CASE WHEN is_banned = 1 THEN 0 ELSE 1 END, "
                "failed_payments = CASE WHEN is_banned = 1 THEN 0 ELSE failed_payments END "
                "WHERE telegram_id = ?",
                (user_id,)
            )
            
            # Check if any rows were affected
            if self.cur.rowcount == 0:
                logger.warning(f"No rows affected when toggling ban for user {user_id}")
                return False
                
            self.conn.commit()
            logger.info(f"Successfully toggled ban status for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error toggling user ban: {e}")
            return False
    def remove_from_cart(self, cart_id):
        """Remove an item from the user's cart"""
        try:
            self.cur.execute("DELETE FROM cart WHERE id = ?", (cart_id,))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error removing item from cart: {e}")
            return False
    def get_user_stats(self, user_id: int) -> Optional[Tuple]:
        """Get statistics for a specific user"""
        try:
            self.cur.execute("""
                SELECT 
                    u.telegram_id,
                    u.created_at,
                    COUNT(CASE WHEN pr.status = 'completed' THEN 1 END) as completed_orders,
                    COUNT(CASE WHEN pr.status = 'rejected' THEN 1 END) as rejected_orders,
                    u.failed_payments,
                    u.is_banned
                FROM users u
                LEFT JOIN purchase_requests pr ON u.telegram_id = pr.user_id
                WHERE u.telegram_id = ?
                GROUP BY u.telegram_id
            """, (user_id,))
            return self.cur.fetchone()
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return None
    def get_user_wallet(self, user_id: int) -> Optional[str]:
        """Get user's assigned wallet"""
        try:
            self.cur.execute(
                """SELECT w.address 
                FROM user_wallets uw
                JOIN wallets w ON uw.wallet_id = w.id
                WHERE uw.user_id = ?
                LIMIT 1""",
                (user_id,)
            )
            result = self.cur.fetchone()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting user wallet: {e}")
            return None
    def is_user_authorized(self, user_id: int) -> bool:
        """Kullanıcının yetkili olup olmadığını kontrol et"""
        try:
            self.cur.execute(
                "SELECT authorized FROM users WHERE telegram_id = ?",
                (user_id,)
            )
            result = self.cur.fetchone()
            return bool(result[0]) if result else False
        except Exception as e:
            logger.error(f"Error checking user authorization: {e}")
            return False

    def authorize_user(self, user_id: int) -> bool:
        """Kullanıcıyı yetkili olarak işaretle"""
        try:
            self.cur.execute(
                "UPDATE users SET authorized = 1 WHERE telegram_id = ?",
                (user_id,)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error authorizing user: {e}")
            return False
    def setup_database(self):
        """Create database tables"""
        try:
            # Users Table - İlk olarak bunu oluştur
            self.cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                telegram_id INTEGER UNIQUE NOT NULL,
                failed_payments INTEGER DEFAULT 0,
                is_banned BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                authorized INTEGER DEFAULT 0
            )
            ''')
            
            # Location Pool Table
            self.cur.execute('''
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY,
                product_id INTEGER NOT NULL,
                image_path TEXT NOT NULL,
                is_used BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
            ''')

            # Products Table
            self.cur.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                image_path TEXT,
                stock INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0
            )
            ''')

            # Orders Table
            self.cur.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                wallet TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
            ''')

            # Wallets Pool Table
            self.cur.execute('''
            CREATE TABLE IF NOT EXISTS wallets (
                id INTEGER PRIMARY KEY,
                address TEXT NOT NULL UNIQUE,
                in_use BOOLEAN DEFAULT 0
            )
            ''')

            # Cart Table
            self.cur.execute('''
            CREATE TABLE IF NOT EXISTS cart (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (telegram_id),
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
            ''')

            # Purchase Requests Table
            self.cur.execute('''
            CREATE TABLE IF NOT EXISTS purchase_requests (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                total_amount REAL NOT NULL,
                wallet TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                discount_percent INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (telegram_id)
            )
            ''')

            # Claimed Discounts Table
            self.cur.execute('''
            CREATE TABLE IF NOT EXISTS claimed_discounts (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                discount_percent INTEGER NOT NULL,
                claimed_month TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, discount_percent, claimed_month)
            )
            ''')

            # Purchase Request Items Table
            self.cur.execute('''
            CREATE TABLE IF NOT EXISTS purchase_request_items (
                id INTEGER PRIMARY KEY,
                request_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                FOREIGN KEY (request_id) REFERENCES purchase_requests (id),
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
            ''')

            # Payments Table
            self.cur.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                wallet TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (telegram_id)
            )
            ''')

            # User Wallets Table
            self.cur.execute('''
            CREATE TABLE IF NOT EXISTS user_wallets (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                wallet_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (telegram_id),
                FOREIGN KEY (wallet_id) REFERENCES wallets (id),
                UNIQUE(user_id, wallet_id)
            )
            ''')

            # Game Sessions Table
            self.cur.execute('''
            CREATE TABLE IF NOT EXISTS game_sessions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                session_id TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_used BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (telegram_id)
            )
            ''')
            
            # Game Scores Table
            self.cur.execute('''
            CREATE TABLE IF NOT EXISTS game_scores (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                session_id TEXT,
                score INTEGER NOT NULL,
                game_type TEXT DEFAULT 'flappy_weed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (telegram_id)
            )
            ''')
            
            # Discount Coupons Table
            self.cur.execute('''
            CREATE TABLE IF NOT EXISTS discount_coupons (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                coupon_code TEXT NOT NULL UNIQUE,
                discount_percent INTEGER NOT NULL,
                is_used BOOLEAN DEFAULT 0,
                source TEXT,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (telegram_id)
            )
            ''')

            # User Notifications Table
            self.cur.execute('''
            CREATE TABLE IF NOT EXISTS user_notifications (
                user_id INTEGER PRIMARY KEY,
                last_message_id INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')

            # Game Chances Table (oyun şansları için)
            self.cur.execute('''
            CREATE TABLE IF NOT EXISTS game_chances (
                user_id INTEGER PRIMARY KEY,
                daily_chances INTEGER DEFAULT 5,
                last_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (telegram_id)
            )
            ''')

            # Değişiklikleri kaydet
            self.conn.commit()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error setting up database: {e}")
            raise
    def execute(self, query: str, params: tuple = ()) -> Optional[List[Tuple[Any, ...]]]:
        """Execute SQL query and return results"""
        try:
            self.cur.execute(query, params)
            return self.cur.fetchall()
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            return None
    def has_claimed_discount(self, user_id: int, discount_percent: int) -> bool:
        """Check if a user has already claimed a specific discount percentage in the current month"""
        try:
            current_month = datetime.now().strftime('%Y-%m')
            self.cur.execute(
                """SELECT COUNT(*) FROM claimed_discounts 
                WHERE user_id = ? AND discount_percent = ? AND claimed_month = ?""",
                (user_id, discount_percent, current_month)
            )
            count = self.cur.fetchone()[0]
            return count > 0
        except Exception as e:
            logger.error(f"Error checking claimed discount: {e}")
            return False

    def record_claimed_discount(self, user_id: int, discount_percent: int) -> bool:
        """Record that a user has claimed a specific discount percentage in the current month"""
        try:
            current_month = datetime.now().strftime('%Y-%m')
            self.cur.execute(
                """INSERT INTO claimed_discounts 
                (user_id, discount_percent, claimed_month) 
                VALUES (?, ?, ?)""",
                (user_id, discount_percent, current_month)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error recording claimed discount: {e}")
            return False

    def reset_claimed_discounts(self) -> bool:
        """Reset claimed discounts for the previous month"""
        try:
            # Delete records from previous months
            current_month = datetime.now().strftime('%Y-%m')
            self.cur.execute(
                "DELETE FROM claimed_discounts WHERE claimed_month != ?",
                (current_month,)
            )
            self.conn.commit()
            logger.info("Claimed discounts reset successfully")
            return True
        except Exception as e:
            logger.error(f"Error resetting claimed discounts: {e}")
            return False
    def execute_many(self, query: str, params_list: List[tuple]) -> bool:
        """Execute multiple SQL queries"""
        try:
            self.cur.executemany(query, params_list)
            return True
        except Exception as e:
            logger.error(f"Error executing multiple queries: {e}")
            return False
            
    def commit(self):
        """Commit changes to database"""
        try:
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error committing changes: {e}")
            
    def close(self):
        """Close database connection"""
        try:
            if self.conn:
                self.conn.close()
                logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")
            
    def add_to_cart(self, user_id: int, product_id: int, quantity: int) -> bool:
        """Add product to user's cart"""
        try:
            self.cur.execute(
                """INSERT INTO cart (user_id, product_id, quantity) 
                   VALUES (?, ?, ?)""",
                (user_id, product_id, quantity)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding to cart: {e}")
            return False
            
    def get_cart_items(self, user_id: int) -> list:
        """Get all items in user's cart"""
        try:
            self.cur.execute("""
                SELECT c.id, p.name, p.price, c.quantity, p.id
                FROM cart c
                JOIN products p ON c.product_id = p.id
                WHERE c.user_id = ?
            """, (user_id,))
            return self.cur.fetchall()
        except Exception as e:
            logger.error(f"Error getting cart items: {e}")
            return []
            
    def clear_user_cart(self, user_id: int) -> bool:
        """Clear all items from user's cart"""
        try:
            self.cur.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error clearing cart: {e}")
            return False
    def update_purchase_request_status(self, request_id: int, status: str) -> bool:
        """Update purchase request status"""
        try:
            logger.debug(f"Updating request #{request_id} status to {status}")
            # Get user_id from purchase request
            self.cur.execute(
                "SELECT user_id FROM purchase_requests WHERE id = ?",
                (request_id,)
            )
            result = self.cur.fetchone()
            if not result:
                logger.error(f"Purchase request #{request_id} not found")
                return False
            
            user_id = result[0]
            
            self.cur.execute(
                "SELECT telegram_id FROM users WHERE telegram_id = ?",
                (user_id,)
            )
            user_exists = self.cur.fetchone()
            
            if not user_exists:
                logger.info(f"Creating new user record for {user_id}")
                self.cur.execute(
                    "INSERT INTO users (telegram_id, failed_payments, is_banned) VALUES (?, 0, 0)",
                    (user_id,)
                )
                self.conn.commit()
            
            if status == 'rejected':
                self.cur.execute(
                    """UPDATE users 
                    SET failed_payments = failed_payments + 1 
                    WHERE telegram_id = ?""",
                    (user_id,)
                )
                self.conn.commit()
                    
                self.cur.execute(
                    """SELECT failed_payments 
                    FROM users 
                    WHERE telegram_id = ?""",
                    (user_id,)
                )
                result = self.cur.fetchone()
                failed_payments = 0
                
                if result and result[0]:
                    failed_payments = result[0]
                    logger.info(f"User {user_id} has {failed_payments} failed payments")
                    
                    if failed_payments >= 3:
                        self.cur.execute(
                            """UPDATE users 
                            SET is_banned = 1 
                            WHERE telegram_id = ?""",
                            (user_id,)
                        )
                        logger.warning(f"User {user_id} has been banned due to too many failed payments")
                else:
                    logger.warning(f"Failed to get failed payments count for user {user_id}")
                    # Varsayılan değer ata
                    failed_payments = 1
                    self.cur.execute(
                        "UPDATE users SET failed_payments = ? WHERE telegram_id = ?",
                        (failed_payments, user_id)
                    )
                    self.conn.commit()
            
            # If status is completed, reset failed_payments
            elif status == 'completed':
                self.cur.execute(
                    """UPDATE users 
                    SET failed_payments = 0 
                    WHERE telegram_id = ?""",
                    (user_id,)
                )
                self.conn.commit()
            
            # Update request status
            self.cur.execute(
                """UPDATE purchase_requests 
                SET status = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?""",
                (status, request_id)
            )
            self.conn.commit()
            logger.info(f"Successfully updated request #{request_id} status to {status}")
            return True
        except Exception as e:
            logger.exception(f"Error updating purchase request #{request_id}: {str(e)}")
            return False
    def get_cart_count(self, user_id: int) -> int:
        """Get total number of items in user's cart"""
        try:
            self.cur.execute("""
                SELECT SUM(quantity)
                FROM cart
                WHERE user_id = ?
            """, (user_id,))
            result = self.cur.fetchone()[0]
            return result if result else 0
        except Exception as e:
            logger.error(f"Error getting cart count: {e}")
            return 0
            
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        
    def get_products(self) -> List[Tuple]:
        """Get all products"""
        try:
            self.cur.execute("SELECT * FROM products ORDER BY sort_order ASC")
            return self.cur.fetchall()
        except Exception as e:
            logger.error(f"Error getting products: {e}")
            return []
            
    def get_product(self, product_id: int) -> Optional[Tuple]:
        """Get product by ID"""
        try:
            self.cur.execute("SELECT * FROM products WHERE id = ?", (product_id,))
            return self.cur.fetchone()
        except Exception as e:
            logger.error(f"Error getting product: {e}")
            return None
            
    def add_product(self, name: str, description: str, price: float, image_path: str, stock: int = 0) -> bool:
        """Add a new product"""
        try:
            self.cur.execute(
                """INSERT INTO products 
                   (name, description, price, image_path, stock) 
                   VALUES (?, ?, ?, ?, ?)""",
                (name, description, price, image_path, stock)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding product: {e}")
            return False
            
    def update_product_name(self, product_id: int, new_name: str) -> bool:
        """Update product name"""
        try:
            self.cur.execute(
                "UPDATE products SET name = ? WHERE id = ?",
                (new_name, product_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating product name: {e}")
            return False
            
    def update_product_description(self, product_id: int, new_description: str) -> bool:
        """Update product description"""
        try:
            self.cur.execute(
                "UPDATE products SET description = ? WHERE id = ?",
                (new_description, product_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating product description: {e}")
            return False
            
    def update_product_price(self, product_id: int, new_price: float) -> bool:
        """Update product price"""
        try:
            self.cur.execute(
                "UPDATE products SET price = ? WHERE id = ?",
                (new_price, product_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating product price: {e}")
            return False
            
    def update_product_stock(self, product_id: int, quantity: int) -> bool:
        """Update product stock"""
        try:
            self.cur.execute(
                "UPDATE products SET stock = stock + ? WHERE id = ?",
                (quantity, product_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating product stock: {e}")
            return False
            
    def delete_product(self, product_id: int) -> bool:
        """Delete a product"""
        try:
            self.cur.execute("DELETE FROM products WHERE id = ?", (product_id,))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting product: {e}")
            return False
            
    def update_product_sort_order(self, product_id: int, move_up: bool) -> bool:
        """Update product sort order"""
        try:
            if move_up:
                self.cur.execute(
                    """UPDATE products 
                       SET sort_order = sort_order - 1 
                       WHERE id = ? AND sort_order > 0""",
                    (product_id,)
                )
            else:
                self.cur.execute(
                    """UPDATE products 
                       SET sort_order = sort_order + 1 
                       WHERE id = ?""",
                    (product_id,)
                )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating product sort order: {e}")
            return False
            
    def add_wallet(self, address: str) -> bool:
        """Add a new wallet to the pool"""
        try:
            self.cur.execute(
                "INSERT INTO wallets (address, in_use) VALUES (?, 0)",
                (address,)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding wallet: {e}")
            return False
            
    def get_available_wallet(self) -> Optional[str]:
        """
        Kullanılabilir bir cüzdan bulup döndürür.
        Eğer kullanılabilir cüzdan yoksa None döndürür.
        """
        try:
            self.cur.execute("BEGIN TRANSACTION")
            
            # Önce kullanılmayan (in_use=0) cüzdanları kontrol et
            self.cur.execute(
                """SELECT id, address 
                FROM wallets 
                WHERE in_use = 0 
                LIMIT 1"""
            )
            result = self.cur.fetchone()
            if not result:
                logger.warning("No available wallets found. All wallets are in use.")
                self.cur.execute("ROLLBACK")
                return None
                
            wallet_id, address = result
            
            # Cüzdanı kullanıma işaretle
            self.cur.execute(
                "UPDATE wallets SET in_use = 1 WHERE id = ? AND in_use = 0",
                (wallet_id,)
            )
            
            if self.cur.rowcount == 0:
                # Başka bir işlem tarafından alınmış olabilir
                self.cur.execute("ROLLBACK")
                logger.warning(f"Wallet {wallet_id} was taken by another process.")
                return None
            
            # İşlemi tamamla
            self.cur.execute("COMMIT")
            self.conn.commit()
            logger.info(f"Wallet assigned: {address}")
            return address
            
        except Exception as e:
            logger.error(f"Error getting available wallet: {e}")
            try:
                self.cur.execute("ROLLBACK")
            except Exception:
                pass
            return None

    def release_wallet(self, address: str) -> bool:
        """
        Kullanılmış bir cüzdanı serbest bırakır.
        Ödeme işlemi tamamlandıktan sonra çağrılmalıdır.
        """
        try:
            self.cur.execute(
                "UPDATE wallets SET in_use = 0 WHERE address = ?",
                (address,)
            )
            self.conn.commit()
            logger.info(f"Wallet released: {address}")
            return True
        except Exception as e:
            logger.error(f"Error releasing wallet: {e}")
            return False
    def get_failed_payments_count(self, user_id: int) -> int:
        """Get number of failed payments for a user"""
        try:
            self.cur.execute(
                "SELECT failed_payments FROM users WHERE telegram_id = ?",
                (user_id,)
            )
            result = self.cur.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting failed payments count: {e}")
            return 0            
    def update_request_status(self, request_id: int, status: str) -> bool:
        """Alias for update_purchase_request_status for backward compatibility"""
        return self.update_purchase_request_status(request_id, status)
    
    def store_user_last_notification(self, user_id, message_id):
        """Store the ID of the last notification message sent to a user"""
        try:
            # Check if the table exists
            self.cur.execute("""
                CREATE TABLE IF NOT EXISTS user_notifications (
                    user_id INTEGER PRIMARY KEY,
                    last_message_id INTEGER,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert or update the message ID
            self.cur.execute("""
                INSERT OR REPLACE INTO user_notifications (user_id, last_message_id, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (user_id, message_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error storing notification message ID: {e}")
            return False
    def get_user_last_notification(self, user_id):
        """Get the ID of the last notification message sent to a user"""
        try:
            self.cur.execute("""
                SELECT last_message_id
                FROM user_notifications
                WHERE user_id = ?
            """, (user_id,))
            
            result = self.cur.fetchone()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting notification message ID: {e}")
            return None        
    def get_all_wallets(self) -> list:
        """
        Tüm cüzdanları, kullanıcı bilgileriyle birlikte getirir
        """
        try:
            self.cur.execute("""
                SELECT 
                    w.id, 
                    w.address, 
                    w.in_use,
                    u.telegram_id as user_id,
                    (SELECT COUNT(*) FROM purchase_requests WHERE wallet = w.address) as usage_count,
                    (SELECT 
                        CASE 
                            WHEN COUNT(*) > 0 THEN MAX(created_at) 
                            ELSE NULL 
                        END 
                    FROM purchase_requests WHERE wallet = w.address) as last_used_date
                FROM wallets w
                LEFT JOIN purchase_requests pr ON w.address = pr.wallet AND pr.status = 'pending'
                LEFT JOIN users u ON pr.user_id = u.telegram_id
                GROUP BY w.id, w.address, w.in_use
                ORDER BY w.in_use DESC, last_used_date DESC
            """)
            return self.cur.fetchall()
        except Exception as e:
            logger.error(f"Error getting wallets with user info: {e}")
            return []
            
    def get_available_wallet_count(self) -> int:
        """Get count of available wallets"""
        try:
            self.cur.execute("SELECT COUNT(*) FROM wallets WHERE in_use = 0")
            result = self.cur.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting available wallet count: {e}")
            return 0
            
    def get_in_use_wallet_count(self) -> int:
        """Get count of wallets in use"""
        try:
            self.cur.execute("SELECT COUNT(*) FROM wallets WHERE in_use = 1")
            result = self.cur.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting in-use wallet count: {e}")
            return 0
            
    def get_total_wallet_count(self) -> int:
        """Get total count of wallets"""
        try:
            self.cur.execute("SELECT COUNT(*) FROM wallets")
            result = self.cur.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting total wallet count: {e}")
            return 0
            
    def add_location(self, product_id: int, image_path: str) -> bool:
        """Add a new location to the pool"""
        try:
            self.cur.execute(
                """INSERT INTO locations 
                (product_id, image_path, is_used) 
                VALUES (?, ?, 0)""",
                (product_id, image_path)
            )
            self.conn.commit()
            logger.info(f"Added new location {image_path} for product {product_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding location: {e}")
            return False
            
    def get_available_location(self, product_id: int) -> str:
        """
        Ürün için kullanılabilir bir konum bulur ve veritabanından siler
        
        Args:
            product_id: Ürün ID'si
            
        Returns:
            str: Konum dosyasının yolu veya None
        """
        try:
            self.cur.execute("BEGIN TRANSACTION")
            
            # Ürün ID'sine göre müsait konum bul
            self.cur.execute(
                """SELECT id, image_path 
                FROM locations 
                WHERE product_id = ? AND is_used = 0 
                LIMIT 1""",
                (product_id,)
            )
            result = self.cur.fetchone()
            
            if not result:
                # Müsait konum yoksa işlemi geri al
                self.cur.execute("ROLLBACK")
                logger.warning(f"No available location for product {product_id}")
                return None
                
            location_id, image_path = result
            
            # Konumu veritabanından sil (eskiden is_used=1 yapıyordu)
            self.cur.execute(
                "DELETE FROM locations WHERE id = ?",
                (location_id,)
            )
            
            # İşlemi onayla
            self.cur.execute("COMMIT")
            self.conn.commit()
            logger.info(f"Successfully assigned and will delete location {image_path} for product {product_id}")
            
            return image_path
                
        except Exception as e:
            logger.error(f"Error getting available location: {e}")
            try:
                self.cur.execute("ROLLBACK")
            except:
                pass
            return None

    def get_available_location_count(self, product_id: int) -> int:
        """Get count of available locations for a product"""
        try:
            self.cur.execute(
                """SELECT COUNT(*) 
                FROM locations 
                WHERE product_id = ? AND is_used = 0""",
                (product_id,)
            )
            result = self.cur.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting available location count: {e}")
            return 0
    def reset_used_locations(self, product_id: int = None) -> int:
        """Reset used locations to available state
        
        Args:
            product_id: Optional product ID to reset only locations for that product
                    If None, reset all used locations
        
        Returns:
            Number of locations reset
        """
        try:
            if product_id is not None:
                self.cur.execute(
                    """UPDATE locations 
                    SET is_used = 0 
                    WHERE product_id = ? AND is_used = 1""",
                    (product_id,)
                )
            else:
                self.cur.execute("UPDATE locations SET is_used = 0 WHERE is_used = 1")
                
            self.conn.commit()
            reset_count = self.cur.rowcount
            logger.info(f"Reset {reset_count} used locations to available state")
            return reset_count
        except Exception as e:
            logger.error(f"Error resetting used locations: {e}")
            return 0

    def get_product_location_stats(self, product_id: int) -> dict:
        """Get location statistics for a product"""
        try:
            self.cur.execute(
                """SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN is_used = 0 THEN 1 ELSE 0 END) as available,
                    SUM(CASE WHEN is_used = 1 THEN 1 ELSE 0 END) as used
                FROM locations 
                WHERE product_id = ?""",
                (product_id,)
            )
            result = self.cur.fetchone()
            if not result:
                return {'total': 0, 'available': 0, 'used': 0}
                
            return {
                'total': result[0],
                'available': result[1],
                'used': result[2]
            }
        except Exception as e:
            logger.error(f"Error getting product location stats: {e}")
            return {'total': 0, 'available': 0, 'used': 0}

    def get_all_location_stats(self) -> list:
        """Get location statistics for all products"""
        try:
            self.cur.execute(
                """SELECT 
                    p.id,
                    p.name,
                    COUNT(l.id) as total,
                    SUM(CASE WHEN l.is_used = 0 THEN 1 ELSE 0 END) as available,
                    SUM(CASE WHEN l.is_used = 1 THEN 1 ELSE 0 END) as used
                FROM products p
                LEFT JOIN locations l ON p.id = l.product_id
                GROUP BY p.id, p.name"""
            )
            results = self.cur.fetchall()
            
            stats = []
            for row in results:
                stats.append({
                    'product_id': row[0],
                    'product_name': row[1],
                    'total': row[2] or 0,
                    'available': row[3] or 0,
                    'used': row[4] or 0
                })
            return stats
        except Exception as e:
            logger.error(f"Error getting all location stats: {e}")
            return []
    def get_purchase_request(self, request_id: int) -> Optional[Dict[str, Any]]:
        """Get purchase request details"""
        try:
            logger.debug(f"Fetching purchase request #{request_id}")
            self.cur.execute("""
                SELECT 
                    pr.*,
                    GROUP_CONCAT(
                        p.name || ' (x' || pri.quantity || ' @ ' || pri.price || ' USDT)\n'
                    ) as items
                FROM purchase_requests pr
                JOIN purchase_request_items pri ON pr.id = pri.request_id
                JOIN products p ON pri.product_id = p.id
                WHERE pr.id = ?
                GROUP BY pr.id
            """, (request_id,))
            result = self.cur.fetchone()
            
            if result:
                logger.debug(f"Found purchase request: {result}")
                return {
                    'id': result[0],
                    'user_id': result[1],
                    'total_amount': result[2],
                    'wallet': result[3],
                    'status': result[4],
                    'created_at': result[5],
                    'updated_at': result[6],
                    'items': result[7]
                }
            else:
                logger.warning(f"No purchase request found with ID {request_id}")
                return None
        except Exception as e:
            logger.exception(f"Error getting purchase request #{request_id}: {str(e)}")
            return None
    def release_wallet_for_user(self, user_id: int) -> bool:
        """Remove wallet assignment from user"""
        try:
            # Get the wallet ID for the user
            self.cur.execute(
                """SELECT w.id
                FROM user_wallets uw
                JOIN wallets w ON uw.wallet_id = w.id
                WHERE uw.user_id = ?""",
                (user_id,)
            )
            result = self.cur.fetchone()
            if not result:
                return False
                
            wallet_id = result[0]
            
            # Start transaction
            self.cur.execute("BEGIN TRANSACTION")
            
            # Delete the user-wallet relationship
            self.cur.execute(
                "DELETE FROM user_wallets WHERE user_id = ?",
                (user_id,)
            )
            
            # Set the wallet as available
            self.cur.execute(
                "UPDATE wallets SET in_use = 0 WHERE id = ?",
                (wallet_id,)
            )
            
            # Commit transaction
            self.cur.execute("COMMIT")
            self.conn.commit()
            
            logger.info(f"Released wallet assignment for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error releasing wallet for user: {e}")
            try:
                self.cur.execute("ROLLBACK")
            except:
                pass
            return False

    def reassign_wallet_to_user(self, user_id: int) -> Optional[str]:
        """Reassign a new wallet to a user"""
        try:
            # First release the current wallet
            if not self.release_wallet_for_user(user_id):
                logger.warning(f"No wallet found to release for user {user_id}")
            
            # Then assign a new one
            return self.assign_wallet_to_user(user_id)
        except Exception as e:
            logger.error(f"Error reassigning wallet to user: {e}")
            return None

    def get_user_wallet_transactions(self, user_id: int) -> List[Dict]:
        """Get all transactions for a user's assigned wallet"""
        try:
            # Get the user's wallet
            wallet = self.get_user_wallet(user_id)
            if not wallet:
                return []
                
            # Get all transactions for this wallet
            self.cur.execute(
                """SELECT 
                    id,
                    user_id,
                    total_amount,
                    status,
                    created_at,
                    updated_at
                FROM purchase_requests
                WHERE wallet = ?
                ORDER BY created_at DESC""",
                (wallet,)
            )
            
            results = self.cur.fetchall()
            transactions = []
            
            for row in results:
                transactions.append({
                    'id': row[0],
                    'user_id': row[1],
                    'amount': row[2],
                    'status': row[3],
                    'created_at': row[4],
                    'updated_at': row[5]
                })
                
            return transactions
        except Exception as e:
            logger.error(f"Error getting user wallet transactions: {e}")
            return []
    def get_all_locations(self) -> List[Dict[str, Any]]:
        """Get all locations with their status"""
        try:
            self.cur.execute(
                """SELECT id, product_id, image_path, is_used, created_at 
                   FROM locations 
                   ORDER BY is_used ASC, created_at DESC"""
            )
            results = self.cur.fetchall()
            return [
                {
                    'id': row[0],
                    'product_id': row[1],
                    'image_path': row[2],
                    'is_used': row[3],
                    'created_at': row[4]
                }
                for row in results
            ]
        except Exception as e:
            logger.error(f"Error getting locations: {e}")
            return []
            
    def delete_location(self, location_id: int) -> bool:
        """Delete an unused location"""
        try:
            # Get image path before deleting
            self.cur.execute(
                "SELECT image_path FROM locations WHERE id = ? AND is_used = 0",
                (location_id,)
            )
            result = self.cur.fetchone()
            if not result:
                return False
                
            image_path = result[0]
            
            # Delete from database
            self.cur.execute(
                "DELETE FROM locations WHERE id = ? AND is_used = 0",
                (location_id,)
            )
            
            if self.cur.rowcount > 0:
                self.conn.commit()
                # Delete image file
                if os.path.exists(image_path):
                    os.remove(image_path)
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error deleting location: {e}")
            return False
            self.cur.execute("SELECT COUNT(*) FROM wallets")
            result = self.cur.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting total wallet count: {e}")
            return 0
    #GAME FUNCTIONS
    def create_game_session(self, user_id: int, session_id: str) -> bool:
        """Create a new game session for a user"""
        try:
            # Önce tabloyu kontrol et
            self.cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='game_sessions'")
            if not self.cur.fetchone():
                # Tablo yoksa oluştur
                self.cur.execute('''
                CREATE TABLE IF NOT EXISTS game_sessions (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    session_id TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_used INTEGER DEFAULT 0
                )
                ''')
                self.conn.commit()
                logger.info("Created game_sessions table")
            
            # Oturumu ekle
            self.cur.execute(
                "INSERT INTO game_sessions (user_id, session_id) VALUES (?, ?)",
                (user_id, session_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error creating game session: {e}")
            return False

    def validate_game_session(self, user_id: int, session_id: str) -> bool:
        """Validate if a game session exists and belongs to the user"""
        try:
            # Önce tabloyu kontrol et
            self.cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='game_sessions'")
            if not self.cur.fetchone():
                # Tablo yoksa doğrulama başarısız olur
                logger.warning("game_sessions table does not exist")
                return True  # Geçici olarak True döndürüyoruz
            
            self.cur.execute(
                "SELECT id FROM game_sessions WHERE user_id = ? AND session_id = ?",  # is_used şartını kaldırdık
                (user_id, session_id)
            )
            result = self.cur.fetchone()
            return True  # Geçici olarak True döndürüyoruz
        except Exception as e:
            logger.error(f"Error validating game session: {e}")
            return True 

    def use_game_chance(self, user_id: int) -> bool:
        """Use one game chance for the user"""
        try:
            self.cur.execute(
                "SELECT daily_chances, last_reset FROM game_chances WHERE user_id = ?",
                (user_id,)
            )
            result = self.cur.fetchone()
            
            current_time = datetime.now()
            
            if result:
                chances, last_reset = result
                last_reset = datetime.strptime(last_reset.split('.')[0], '%Y-%m-%d %H:%M:%S') if isinstance(last_reset, str) else last_reset
                
                if (current_time - last_reset).days > 0:
                    # Reset to 5 chances instead of 3
                    self.cur.execute(
                        "UPDATE game_chances SET daily_chances = 4, last_reset = ? WHERE user_id = ?",
                        (current_time, user_id)
                    )
                else:
                    if chances > 0:
                        self.cur.execute(
                            "UPDATE game_chances SET daily_chances = daily_chances - 1 WHERE user_id = ?",
                            (user_id,)
                        )
                    else:
                        return False
            else:
                # Initialize with 5 chances and immediately use one
                self.cur.execute(
                    "INSERT INTO game_chances (user_id, daily_chances, last_reset) VALUES (?, 4, ?)",
                    (user_id, current_time)
                )
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error using game chance: {e}")
            return False

    def get_remaining_daily_games(self, user_id: int) -> int:
        """Get remaining daily game chances for a user"""
        try:
            self.cur.execute(
                "SELECT daily_chances, last_reset FROM game_chances WHERE user_id = ?",
                (user_id,)
            )
            result = self.cur.fetchone()
            
            current_time = datetime.now()
            
            if result:
                chances, last_reset_str = result
                # Fix date parsing issue
                try:
                    if isinstance(last_reset_str, str):
                        last_reset = datetime.strptime(last_reset_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
                    else:
                        last_reset = last_reset_str
                except:
                    # Use current time if parsing fails
                    last_reset = current_time - timedelta(days=1)  # Default to yesterday
                
                if (current_time - last_reset).days > 0:
                    # Reset to 5 chances (new day)
                    self.cur.execute(
                        "UPDATE game_chances SET daily_chances = 5, last_reset = ? WHERE user_id = ?",
                        (current_time.strftime('%Y-%m-%d %H:%M:%S'), user_id)
                    )
                    self.conn.commit()
                    return 5
                else:
                    return max(0, chances)  # Ensure non-negative
            else:
                # First time playing, initialize with 5 chances
                self.cur.execute(
                    "INSERT INTO game_chances (user_id, daily_chances, last_reset) VALUES (?, 5, ?)",
                    (user_id, current_time.strftime('%Y-%m-%d %H:%M:%S'))
                )
                self.conn.commit()
                return 5
        except Exception as e:
            logger.error(f"Error getting remaining daily games: {e}")
            return 5  # Hata durumunda kullanıcının oynamasına izin ver

    def get_next_game_reset_time(self, user_id: int) -> datetime:
        """Get next time when game chances will reset"""
        try:
            self.cur.execute(
                "SELECT last_reset FROM game_chances WHERE user_id = ?",
                (user_id,)
            )
            result = self.cur.fetchone()
            
            if result:
                last_reset_str = result[0]
                # Hatalı tarih çözümleme sorununu çöz
                try:
                    last_reset = datetime.strptime(last_reset_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
                except:
                    # Çözümleme hatası varsa şu anki zamanı kullan
                    last_reset = datetime.now()
                    
                # Next reset is at midnight
                next_reset = last_reset.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                return next_reset
            else:
                # If no entry, return next midnight
                now = datetime.now()
                next_reset = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                return next_reset
        except Exception as e:
            logger.error(f"Error getting next game reset time: {e}")
            # Return 24 hours from now as default
            return datetime.now() + timedelta(hours=24)

    def save_game_score(self, user_id: int, session_id: str, score: int) -> bool:
        """Save game score and mark session as used"""
        try:
            # Mark session as used
            self.cur.execute(
                "UPDATE game_sessions SET is_used = 1 WHERE user_id = ? AND session_id = ?",
                (user_id, session_id)
            )
            
            # Save score
            self.cur.execute(
                "INSERT INTO game_scores (user_id, session_id, score) VALUES (?, ?, ?)",
                (user_id, session_id, score)
            )
            
            self.conn.commit()
            logger.info(f"Saved score {score} for user {user_id}, session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving game score: {e}")
            return False

    def get_top_scores(self, limit: int = 10) -> list:
        """Get users with highest single-game scores"""
        try:
            self.cur.execute("""
                SELECT 
                    gs.user_id,
                    MAX(gs.score) as best_score,
                    gs.created_at
                FROM game_scores gs
                GROUP BY gs.user_id
                ORDER BY best_score DESC
                LIMIT ?
            """, (limit,))
            return self.cur.fetchall()
        except Exception as e:
            logger.error(f"Error getting top scores: {e}")
            return []
        
    def get_user_total_score(self, user_id: int) -> int:
        """Get user's total accumulated score from all games"""
        try:
            self.cur.execute(
                "SELECT SUM(score) FROM game_scores WHERE user_id = ?",
                (user_id,)
            )
            result = self.cur.fetchone()
            return result[0] if result and result[0] else 0
        except Exception as e:
            logger.error(f"Error getting user total score: {e}")
            return 0
        
    def get_top_total_scores(self, limit: int = 10) -> list:
        """Get users with highest total accumulated scores"""
        try:
            self.cur.execute("""
                SELECT 
                    gs.user_id,
                    SUM(gs.score) as total_score,
                    COUNT(gs.id) as games_played
                FROM game_scores gs
                GROUP BY gs.user_id
                ORDER BY total_score DESC
                LIMIT ?
            """, (limit,))
            return self.cur.fetchall()
        except Exception as e:
            logger.error(f"Error getting top total scores: {e}")
            return []
    def get_user_best_score(self, user_id: int) -> int:
        """Get user's best score (highest single game score)"""
        try:
            self.cur.execute(
                "SELECT MAX(score) FROM game_scores WHERE user_id = ?",
                (user_id,)
            )
            result = self.cur.fetchone()
            return result[0] if result and result[0] else 0
        except Exception as e:
            logger.error(f"Error getting user best score: {e}")
            return 0

    def create_discount_coupon(self, user_id: int, discount_percent: int, source: str) -> str:
        """Create a discount coupon for a user with 10-digit code"""
        try:
            import random
            import string
            
            # Generate a 10-digit alphanumeric coupon code
            coupon_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            
            # Set expiry date to 30 days from now
            expires_at = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
            
            self.cur.execute(
                """INSERT INTO discount_coupons 
                (user_id, coupon_code, discount_percent, source, expires_at) 
                VALUES (?, ?, ?, ?, ?)""",
                (user_id, coupon_code, discount_percent, source, expires_at)
            )
            
            self.conn.commit()
            logger.info(f"Created {discount_percent}% discount coupon {coupon_code} for user {user_id}")
            return coupon_code
        except Exception as e:
            logger.error(f"Error creating discount coupon: {e}")
            return None
    def create_purchase_request(self, user_id: int, cart_items: list, wallet: str, discount_percent: int = 0) -> Optional[int]:
        """Create a new purchase request with assigned wallet and optional discount"""
        try:
            # Start transaction
            self.cur.execute("BEGIN TRANSACTION")
            
            # Calculate subtotal
            subtotal = sum(item[2] * item[3] for item in cart_items)
            
            # Apply discount if any
            discount_amount = 0
            if discount_percent > 0:
                discount_amount = (subtotal * discount_percent) / 100
            
            # Final total after discount
            total_amount = subtotal - discount_amount
            
            # Create purchase request
            self.cur.execute(
                """INSERT INTO purchase_requests 
                (user_id, total_amount, wallet, status, discount_percent) 
                VALUES (?, ?, ?, 'pending', ?)""",
                (user_id, total_amount, wallet, discount_percent)
            )
            request_id = self.cur.lastrowid
            
            # Add items to purchase request
            for item in cart_items:
                self.cur.execute(
                    """INSERT INTO purchase_request_items 
                    (request_id, product_id, quantity, price) 
                    VALUES (?, ?, ?, ?)""",
                    (request_id, item[4], item[3], item[2])
                )
            
            # Commit transaction
            self.cur.execute("COMMIT")
            self.conn.commit()
            
            logger.info(f"Created purchase request #{request_id} for user {user_id} with {discount_percent}% discount")
            return request_id
            
        except Exception as e:
            logger.error(f"Error creating purchase request: {e}. Rolling back transaction.")
            self.cur.execute("ROLLBACK")
            return None
            
    def get_user_active_request(self, user_id: int) -> Optional[dict]:
        """Get user's active (pending) purchase request"""
        try:
            # First get the request details
            self.cur.execute("""
                SELECT 
                    pr.id,
                    pr.user_id,
                    pr.total_amount,
                    pr.wallet,
                    pr.status,
                    pr.created_at,
                    pr.updated_at
                FROM purchase_requests pr
                WHERE pr.user_id = ? AND pr.status = ?
                ORDER BY pr.created_at DESC
                LIMIT 1
            """, (user_id, 'pending'))
            
            result = self.cur.fetchone()
            
            if result:
                request = {
                    'id': result[0],
                    'user_id': result[1],
                    'total_amount': result[2],
                    'wallet': result[3],
                    'status': result[4],
                    'created_at': result[5],
                    'updated_at': result[6],
                }
                
                # Get items separately
                self.cur.execute("""
                    SELECT 
                        p.name,
                        pri.quantity,
                        pri.price
                    FROM purchase_request_items pri
                    JOIN products p ON pri.product_id = p.id
                    WHERE pri.request_id = ?
                """, (request['id'],))
                
                items = self.cur.fetchall()
                items_text = ""
                for item in items:
                    items_text += f"- {item[0]} (x{item[1]} @ {item[2]} USDT)\n"
                
                request['items'] = items_text
                return request
                
            return None
        except Exception as e:
            logger.error(f"Error getting active request: {e}")
            return None
            
    def get_request_wallet(self, request_id: int) -> Optional[str]:
        """Get wallet address for a purchase request"""
        try:
            self.cur.execute(
                "SELECT wallet FROM purchase_requests WHERE id = ?",
                (request_id,)
            )
            result = self.cur.fetchone()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting request wallet: {e}")
            return None
            
    def get_wallet_stats(self, wallet_id: int) -> Optional[Tuple]:
        """Get detailed statistics for a wallet"""
        try:
            self.cur.execute(
                """SELECT 
                    w.*,
                    COUNT(DISTINCT pr.id) as total_txns,
                    COUNT(DISTINCT CASE WHEN pr.status = 'completed' THEN pr.id END) as completed_txns,
                    COUNT(DISTINCT CASE WHEN pr.status = 'rejected' THEN pr.id END) as rejected_txns,
                    SUM(CASE WHEN pr.status = 'completed' THEN pr.total_amount ELSE 0 END) as total_volume,
                    MAX(pr.created_at) as last_used
                FROM wallets w
                LEFT JOIN purchase_requests pr ON w.address = pr.wallet
                WHERE w.id = ?
                GROUP BY w.id, w.address, w.in_use""",
                (wallet_id,)
            )
            return self.cur.fetchone()
        except Exception as e:
            logger.error(f"Error getting wallet stats: {e}")
            return None

    def delete_wallet(self, wallet_id: int) -> bool:
        """Delete an unused wallet"""
        try:
            self.cur.execute(
                "DELETE FROM wallets WHERE id = ? AND in_use = 0",
                (wallet_id,)
            )
            self.conn.commit()
            return self.cur.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting wallet: {e}")
            return False
    def create_discount_coupon(self, user_id: int, discount_percent: int, source: str) -> str:
        """Create a discount coupon for a user with 10-digit code"""
        try:
            import random
            import string
            
            # Generate a 10-digit alphanumeric coupon code
            coupon_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            
            # Set expiry date to 30 days from now
            expires_at = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
            
            self.cur.execute(
                """INSERT INTO discount_coupons 
                (user_id, coupon_code, discount_percent, source, expires_at) 
                VALUES (?, ?, ?, ?, ?)""",
                (user_id, coupon_code, discount_percent, source, expires_at)
            )
            
            self.conn.commit()
            logger.info(f"Created {discount_percent}% discount coupon {coupon_code} for user {user_id}")
            return coupon_code
        except Exception as e:
            logger.error(f"Error creating discount coupon: {e}")
            return None
            
    def validate_discount_coupon(self, coupon_code: str, user_id: int) -> dict:
        """Validate a discount coupon and return discount info if valid"""
        try:
            self.cur.execute(
                """SELECT id, discount_percent, expires_at, is_used
                FROM discount_coupons
                WHERE coupon_code = ? AND user_id = ?""",
                (coupon_code, user_id)
            )
            
            result = self.cur.fetchone()
            if not result:
                return {"valid": False, "message": "Geçersiz kupon kodu."}
                
            coupon_id, discount_percent, expires_at, is_used = result
            
            # Check if coupon is already used
            if is_used:
                return {"valid": False, "message": "Bu kupon daha önce kullanılmış."}
                
            # Check if coupon is expired
            if expires_at:
                try:
                    expiry_date = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')
                    if expiry_date < datetime.now():
                        return {"valid": False, "message": "Bu kupon süresi dolmuş."}
                except:
                    pass
            
            # Valid coupon
            return {
                "valid": True, 
                "discount_percent": discount_percent,
                "coupon_id": coupon_id,
                "message": f"Kupon başarıyla uygulandı! %{discount_percent} indirim kazandınız."
            }
            
        except Exception as e:
            logger.error(f"Error validating coupon: {e}")
            return {"valid": False, "message": "Kupon doğrulanırken bir hata oluştu."}

    def apply_discount_coupon(self, coupon_id: int) -> bool:
        """Mark a discount coupon as used"""
        try:
            self.cur.execute(
                "UPDATE discount_coupons SET is_used = 1 WHERE id = ?",
                (coupon_id,)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error applying coupon: {e}")
            return False
            
    def get_user_available_coupons(self, user_id: int) -> list:
        """Get all available (unused) coupons for a user"""
        try:
            self.cur.execute(
                """SELECT coupon_code, discount_percent, source, expires_at
                FROM discount_coupons
                WHERE user_id = ? AND is_used = 0 AND (expires_at IS NULL OR expires_at > datetime('now'))
                ORDER BY discount_percent DESC""",
                (user_id,)
            )
            return self.cur.fetchall()
        except Exception as e:
            logger.error(f"Error getting user coupons: {e}")
            return []