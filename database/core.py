import sqlite3
import logging
from typing import Optional, List, Tuple, Any, Dict
import os

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
            logger.info(f"Wallet {address} assigned to user {user_id}")
            return address
            
        except Exception as e:
            logger.error(f"Error assigning wallet to user: {e}")
            try:
                self.cur.execute("ROLLBACK")
            except:
                pass
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
    def setup_database(self):
        """Create database tables"""
        try:
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

            # Users Table
            self.cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                telegram_id INTEGER UNIQUE NOT NULL,
                failed_payments INTEGER DEFAULT 0,
                is_banned BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                FOREIGN KEY (user_id) REFERENCES users (telegram_id)
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
            # Yeni kullanıcı-cüzdan ilişki tablosu
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
            
            # Önce kullanıcının varlığını kontrol et ve gerekirse oluştur
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
            
            # If status is rejected, increment failed_payments
            if status == 'rejected':
                self.cur.execute(
                    """UPDATE users 
                    SET failed_payments = failed_payments + 1 
                    WHERE telegram_id = ?""",
                    (user_id,)
                )
                self.conn.commit()
                    
                # Check if user should be banned
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
        """Get an available wallet and mark it as in use"""
        try:
            self.cur.execute("BEGIN TRANSACTION")
            
            self.cur.execute(
                """SELECT id, address 
                   FROM wallets 
                   WHERE in_use = 0 
                   LIMIT 1"""
            )
            result = self.cur.fetchone()
            if not result:
                self.cur.execute("ROLLBACK")
                return None
                
            wallet_id, address = result
            
            # Mark wallet as in use
            self.cur.execute(
                "UPDATE wallets SET in_use = 1 WHERE id = ? AND in_use = 0",
                (wallet_id,)
            )
            
            if self.cur.rowcount == 0:
                # Another process got the wallet first
                self.cur.execute("ROLLBACK")
                return None
            
            self.cur.execute("COMMIT")
            self.conn.commit()
            logger.info(f"Successfully assigned wallet: {address}")
            return address
            
        except Exception as e:
            logger.error(f"Error getting available wallet: {e}. Rolling back transaction.")
            self.cur.execute("ROLLBACK")
            
    def release_wallet(self, address: str) -> bool:
        """Mark a wallet as available"""
        try:
            self.cur.execute(
                "UPDATE wallets SET in_use = 0 WHERE address = ?",
                (address,)
            )
            self.conn.commit()
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

    def get_all_wallets(self) -> List[Tuple]:
        """Get all wallets with their status"""
        try:
            self.cur.execute("SELECT * FROM wallets ORDER BY in_use ASC")
            return self.cur.fetchall()
        except Exception as e:
            logger.error(f"Error getting wallets: {e}")
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
            
    def get_available_location(self, product_id: int) -> Optional[str]:
        """Get an available location and mark it as used"""
        try:
            self.cur.execute("BEGIN TRANSACTION")
            
            # Önce ürün ID'sine göre müsait konum var mı kontrol et
            self.cur.execute(
                """SELECT id, image_path 
                FROM locations 
                WHERE product_id = ? AND is_used = 0 
                LIMIT 1""",
                (product_id,)
            )
            result = self.cur.fetchone()
            
            if not result:
                # Hiç müsait konum yoksa işlemi geri al
                self.cur.execute("ROLLBACK")
                logger.warning(f"No available location for product {product_id}")
                return None
                
            location_id, image_path = result
            
            # Konumu kullanıldı olarak işaretle
            self.cur.execute(
                "UPDATE locations SET is_used = 1 WHERE id = ? AND is_used = 0",
                (location_id,)
            )
            
            if self.cur.rowcount == 0:
                # Başka bir işlem konumu alırsa işlemi geri al
                self.cur.execute("ROLLBACK")
                logger.warning(f"Location {location_id} was already in use")
                return None
            
            # İşlemi onayla
            self.cur.execute("COMMIT")
            self.conn.commit()
            logger.info(f"Successfully assigned location {image_path} for product {product_id}")
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
            
    def create_purchase_request(self, user_id: int, cart_items: list, wallet: str) -> Optional[int]:
        """Create a new purchase request with assigned wallet"""
        try:
            # Start transaction
            self.cur.execute("BEGIN TRANSACTION")
            
            # Calculate total amount
            total_amount = sum(item[2] * item[3] for item in cart_items)
            
            # Create purchase request
            self.cur.execute(
                """INSERT INTO purchase_requests 
                   (user_id, total_amount, wallet, status) 
                   VALUES (?, ?, ?, 'pending')""",
                (user_id, total_amount, wallet)
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
            
            logger.info(f"Created purchase request #{request_id} for user {user_id}")
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