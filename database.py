import sqlite3
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
class Database:
    def __init__(self, db_name):
        logger.info(f"Initializing database connection to {db_name}")
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cur = self.conn.cursor()
        self.setup_database()

    def setup_database(self):
        self.cur.execute('''
        DROP TABLE IF EXISTS users;
        DROP TABLE IF EXISTS purchase_requests;
        DROP TABLE IF EXISTS purchase_request_items;
        DROP TABLE IF EXISTS wallets;
        ''')

        self.cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            telegram_id INTEGER UNIQUE NOT NULL,
            failed_payments INTEGER DEFAULT 0,
            is_banned BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

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

        self.cur.execute('''
        CREATE TABLE IF NOT EXISTS wallets (
            id INTEGER PRIMARY KEY,
            address TEXT NOT NULL UNIQUE,
            in_use BOOLEAN DEFAULT 0
        )
        ''')
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

        self.conn.commit()

    def add_product(self, name, description, price, image_path, stock=0):
        try:
            self.cur.execute(
                "INSERT INTO products (name, description, price, image_path, stock) VALUES (?, ?, ?, ?, ?)",
                (name, description, price, image_path, stock)
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error adding product: {e}")
            return False

    def get_all_users_with_stats(self):
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

    def get_user_stats(self, user_id):
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

    def toggle_user_ban(self, user_id):
        """Toggle user ban status"""
        try:
            self.cur.execute(
                "UPDATE users SET is_banned = NOT is_banned WHERE telegram_id = ?",
                (user_id,)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error toggling user ban: {e}")
            return False

    def create_purchase_request(self, user_id, cart_items, wallet):
        """Create a new purchase request with assigned wallet"""
        try:
            self.cur.execute("BEGIN TRANSACTION")
            total_amount = sum(item[2] * item[3] for item in cart_items)
            
            self.cur.execute(
                """INSERT INTO purchase_requests 
                   (user_id, total_amount, wallet, status) 
                   VALUES (?, ?, ?, 'pending')""",
                (user_id, total_amount, wallet)
            )
            request_id = self.cur.lastrowid
            
            for item in cart_items:
                self.cur.execute(
                    """INSERT INTO purchase_request_items 
                       (request_id, product_id, quantity, price) 
                       VALUES (?, ?, ?, ?)""",
                    (request_id, item[4], item[3], item[2])
                )
            
            self.cur.execute("COMMIT")
            self.conn.commit()
            return request_id
            
        except Exception as e:
            self.cur.execute("ROLLBACK")
            logger.error(f"Error creating purchase request: {e}")
            return None

    def get_pending_purchase_requests(self):
        self.cur.execute("""
            SELECT 
                pr.id,
                pr.user_id,
                pr.total_amount,
                pr.created_at,
                GROUP_CONCAT(
                    p.name || ' (x' || pri.quantity || ' @ ' || pri.price || ' USDT)'
                ) as items
            FROM purchase_requests pr
            JOIN purchase_request_items pri ON pr.id = pri.request_id
            JOIN products p ON pri.product_id = p.id
            WHERE pr.status = 'pending'
            GROUP BY pr.id
            ORDER BY pr.created_at DESC
        """)
        return self.cur.fetchall()

    def get_purchase_request(self, request_id):
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

    def update_purchase_request_status(self, request_id, status):
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
            
            # If status is rejected, increment failed_payments
            if status == 'rejected':
                self.cur.execute(
                    """UPDATE users 
                       SET failed_payments = failed_payments + 1 
                       WHERE telegram_id = ?""",
                    (user_id,)
                )
                
                # Check if user should be banned
                self.cur.execute(
                    """SELECT failed_payments 
                       FROM users 
                       WHERE telegram_id = ?""",
                    (user_id,)
                )
                failed_payments = self.cur.fetchone()[0]
                
                if failed_payments >= 3:
                    self.cur.execute(
                        """UPDATE users 
                           SET is_banned = 1 
                           WHERE telegram_id = ?""",
                        (user_id,)
                    )
                    logger.warning(f"User {user_id} has been banned due to too many failed payments")
            
            # If status is completed, reset failed_payments
            elif status == 'completed':
                self.cur.execute(
                    """UPDATE users 
                       SET failed_payments = 0 
                       WHERE telegram_id = ?""",
                    (user_id,)
                )
            
            self.cur.execute(
                "UPDATE purchase_requests SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, request_id)
            )
            self.conn.commit()
            logger.info(f"Successfully updated request #{request_id} status")
            return True
        except Exception as e:
            logger.exception(f"Error updating purchase request #{request_id}: {str(e)}")
            return False

    def is_user_banned(self, user_id):
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

    def get_failed_payments_count(self, user_id):
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

    def clear_user_cart(self, user_id):
        self.cur.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def add_to_cart(self, user_id, product_id, quantity):
        try:
            self.cur.execute(
                "INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)",
                (user_id, product_id, quantity)
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error adding to cart: {e}")
            return False

    def get_cart_items(self, user_id):
        self.cur.execute("""
            SELECT c.id, p.name, p.price, c.quantity, p.id
            FROM cart c
            JOIN products p ON c.product_id = p.id
            WHERE c.user_id = ?
        """, (user_id,))
        return self.cur.fetchall()

    def get_cart_count(self, user_id):
        """Get total number of items in user's cart"""
        self.cur.execute("""
            SELECT SUM(quantity)
            FROM cart
            WHERE user_id = ?
        """, (user_id,))
        result = self.cur.fetchone()[0]
        return result if result else 0

    def remove_from_cart(self, cart_id):
        """Remove an item from the user's cart"""
        try:
            self.cur.execute("DELETE FROM cart WHERE id = ?", (cart_id,))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error removing item from cart: {e}")
            return False
    def update_product_stock(self, product_id, quantity):
        try:
            self.cur.execute(
                "UPDATE products SET stock = stock + ? WHERE id = ?",
                (quantity, product_id)
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error updating stock: {e}")
            return False

    def update_product_name(self, product_id, new_name):
        self.cur.execute(
            "UPDATE products SET name = ? WHERE id = ?",
            (new_name, product_id)
        )
        self.conn.commit()

    def update_product_description(self, product_id, new_description):
        self.cur.execute(
            "UPDATE products SET description = ? WHERE id = ?",
            (new_description, product_id)
        )
        self.conn.commit()

    def update_product_price(self, product_id, new_price):
        self.cur.execute(
            "UPDATE products SET price = ? WHERE id = ?",
            (new_price, product_id)
        )
        self.conn.commit()

    def get_products(self):
        self.cur.execute("SELECT * FROM products")
        return self.cur.fetchall()

    def get_product(self, product_id):
        self.cur.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        return self.cur.fetchone()

    def delete_product(self, product_id):
        self.cur.execute("DELETE FROM products WHERE id = ?", (product_id,))
        self.conn.commit()

    def get_user_orders_by_status(self, user_id, status):
        """Get user's purchase requests filtered by status"""
        try:
            query = """
                SELECT 
                    pr.id,
                    pr.user_id,
                    pr.total_amount,
                    pr.status,
                    pr.created_at,
                    GROUP_CONCAT(
                        p.name || ' (x' || pri.quantity || ' @ ' || pri.price || ' USDT)'
                    ) as items
                FROM purchase_requests pr
                JOIN purchase_request_items pri ON pr.id = pri.request_id
                JOIN products p ON pri.product_id = p.id
                WHERE pr.user_id = ? AND pr.status = ?
                GROUP BY pr.id
                ORDER BY pr.created_at DESC
            """
            
            self.cur.execute(query, (user_id, status))
            return self.cur.fetchall()
        except Exception as e:
            logger.error(f"Error getting orders by status: {e}")
            return []

    def add_wallet(self, address):
        self.cur.execute("INSERT INTO wallets (address) VALUES (?)", (address,))
        self.conn.commit()

    def get_available_wallet(self):
        self.cur.execute("SELECT address FROM wallets WHERE in_use = 0 LIMIT 1")
        result = self.cur.fetchone()
        if result:
            self.cur.execute("UPDATE wallets SET in_use = 1 WHERE address = ?", (result[0],))
            self.conn.commit()
            return result[0]
        return None

    def create_order(self, user_id, product_id, wallet):
        self.cur.execute(
            "INSERT INTO orders (user_id, product_id, wallet) VALUES (?, ?, ?)",
            (user_id, product_id, wallet)
        )
        self.conn.commit()
        return self.cur.lastrowid

    def update_order_status(self, order_id, status):
        self.cur.execute(
            "UPDATE orders SET status = ? WHERE id = ?",
            (status, order_id)
        )
        self.conn.commit()

    def get_pending_orders(self):
        self.cur.execute("""
            SELECT o.id, o.user_id, p.name, p.price, o.wallet 
            FROM orders o 
            JOIN products p ON o.product_id = p.id 
            WHERE o.status = 'pending'
        """)
        return self.cur.fetchall()

    def get_all_users(self):
        """Get all non-banned user IDs from the database"""
        try:
            self.cur.execute("SELECT DISTINCT telegram_id FROM users WHERE is_banned = 0")
            users = [int(row[0]) for row in self.cur.fetchall()]
            logger.info(f"Retrieved {len(users)} users from database")
            return users
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return []

    def get_all_wallets(self):
        """Get all wallets from the database"""
        try:
            self.cur.execute("SELECT * FROM wallets ORDER BY in_use ASC")
            return self.cur.fetchall()
        except Exception as e:
            logger.error(f"Error getting wallets: {e}")
            return []

    def delete_wallet(self, wallet_id):
        """Delete a wallet from the pool"""
        try:
            self.cur.execute(
                "DELETE FROM wallets WHERE id = ? AND in_use = 0",
                (wallet_id,)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting wallet: {e}")
            return False

    def add_user(self, telegram_id):
        """Add new user to the database if not exists"""
        try:
            # Check if user already exists
            self.cur.execute("SELECT telegram_id FROM users WHERE telegram_id = ?", (telegram_id,))
            if self.cur.fetchone():
                logger.debug(f"User {telegram_id} already exists in database")
                return True

            # Add new user
            self.cur.execute(
                "INSERT INTO users (telegram_id, failed_payments, is_banned) VALUES (?, 0, 0)",
                (telegram_id,)
            )
            self.conn.commit()
            logger.info(f"Successfully added user {telegram_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding user {telegram_id}: {e}")
            return False

    def get_user_active_request(self, user_id):
        """Get user's active (pending) purchase request"""
        try:
            self.cur.execute("""
                SELECT 
                    pr.*,
                    GROUP_CONCAT(
                        p.name || ' (x' || pri.quantity || ' @ ' || pri.price || ' USDT)\n'
                    ) as items
                FROM purchase_requests pr
                JOIN purchase_request_items pri ON pr.id = pri.request_id
                JOIN products p ON pri.product_id = p.id
                WHERE pr.user_id = ? AND pr.status = 'pending'
                GROUP BY pr.id
                ORDER BY pr.created_at DESC
                LIMIT 1
            """, (user_id,))
            result = self.cur.fetchone()
            
            if result:
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
            return None
        except Exception as e:
            logger.error(f"Error getting active request: {e}")
            return None

    def get_request_wallet(self, request_id):
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

    def get_available_wallet_count(self):
        """Get count of available wallets"""
        try:
            self.cur.execute("SELECT COUNT(*) FROM wallets WHERE in_use = 0")
            return self.cur.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting available wallet count: {e}")
            return 0

    def get_in_use_wallet_count(self):
        """Get count of wallets in use"""
        try:
            self.cur.execute("SELECT COUNT(*) FROM wallets WHERE in_use = 1")
            return self.cur.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting in-use wallet count: {e}")
            return 0

    def get_total_wallet_count(self):
        """Get total count of wallets"""
        try:
            self.cur.execute("SELECT COUNT(*) FROM wallets")
            return self.cur.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting total wallet count: {e}")
            return 0

    def get_wallet_total_amount(self, wallet):
        """Get total amount processed by a wallet"""
        try:
            self.cur.execute("""
                SELECT SUM(total_amount)
                FROM purchase_requests
                WHERE wallet = ? AND status = 'completed'
            """, (wallet,))
            result = self.cur.fetchone()[0]
            return result if result else 0
        except Exception as e:
            logger.error(f"Error getting wallet total amount: {e}")
            return 0

    def get_general_stats(self):
        """Get general statistics"""
        try:
            stats = {}
            
            # User statistics
            self.cur.execute("""
                SELECT 
                    COUNT(*) as total_users,
                    SUM(CASE WHEN is_banned = 1 THEN 1 ELSE 0 END) as banned_users,
                    SUM(CASE WHEN created_at >= datetime('now', '-1 day') THEN 1 ELSE 0 END) as new_users_24h
                FROM users
            """)
            user_stats = self.cur.fetchone()
            stats.update({
                'total_users': user_stats[0],
                'banned_users': user_stats[1],
                'new_users_24h': user_stats[2]
            })
            
            # Order statistics
            self.cur.execute("""
                SELECT 
                    COUNT(*) as total_orders,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_orders,
                    SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected_orders,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_orders,
                    SUM(CASE WHEN status = 'completed' THEN total_amount ELSE 0 END) as total_revenue,
                    AVG(CASE WHEN status = 'completed' THEN total_amount END) as avg_order_value,
                    MAX(CASE WHEN status = 'completed' THEN total_amount END) as max_order_value
                FROM purchase_requests
            """)
            order_stats = self.cur.fetchone()
            stats.update({
                'total_orders': order_stats[0],
                'completed_orders': order_stats[1],
                'rejected_orders': order_stats[2],
                'pending_orders': order_stats[3],
                'total_revenue': order_stats[4],
                'avg_order_value': round(order_stats[5], 2) if order_stats[5] else 0,
                'max_order_value': order_stats[6] if order_stats[6] else 0
            })
            
            # Calculate rates
            total_processed = stats['completed_orders'] + stats['rejected_orders']
            stats['approval_rate'] = round((stats['completed_orders'] / total_processed * 100) if total_processed > 0 else 0, 2)
            stats['success_rate'] = round((stats['completed_orders'] / stats['total_orders'] * 100) if stats['total_orders'] > 0 else 0, 2)
            
            # Active users in last 7 days
            self.cur.execute("""
                SELECT COUNT(DISTINCT user_id)
                FROM purchase_requests
                WHERE created_at >= datetime('now', '-7 days')
            """)
            stats['active_users_7d'] = self.cur.fetchone()[0]
            
            # Average approval time
            self.cur.execute("""
                SELECT AVG(
                    CAST(
                        (JULIANDAY(updated_at) - JULIANDAY(created_at)) * 24 * 60 
                    AS INTEGER)
                )
                FROM purchase_requests
                WHERE status IN ('completed', 'rejected')
            """)
            avg_minutes = self.cur.fetchone()[0]
            stats['avg_approval_time'] = f"{int(avg_minutes)} dakika" if avg_minutes else "N/A"
            
            # Wallet statistics
            stats.update({
                'available_wallets': self.get_available_wallet_count(),
                'in_use_wallets': self.get_in_use_wallet_count(),
                'total_wallets': self.get_total_wallet_count()
            })
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting general stats: {e}")
            return {}