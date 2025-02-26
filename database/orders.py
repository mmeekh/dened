from typing import Optional, List, Tuple, Dict, Any
from .core import Database
import logging

logger = logging.getLogger(__name__)

class OrdersDB:
    def __init__(self, db: Database):
        self.db = db
        
    def create_purchase_request(self, user_id: int, cart_items: List[Tuple], wallet: str) -> Optional[int]:
        """Create a new purchase request with assigned wallet"""
        try:
            self.db.execute("BEGIN TRANSACTION")
            total_amount = sum(item[2] * item[3] for item in cart_items)
            
            self.db.execute(
                """INSERT INTO purchase_requests 
                   (user_id, total_amount, wallet, status) 
                   VALUES (?, ?, ?, 'pending')""",
                (user_id, total_amount, wallet)
            )
            request_id = self.db.cur.lastrowid
            
            for item in cart_items:
                self.db.execute(
                    """INSERT INTO purchase_request_items 
                       (request_id, product_id, quantity, price) 
                       VALUES (?, ?, ?, ?)""",
                    (request_id, item[4], item[3], item[2])
                )
            
            self.db.execute("COMMIT")
            self.db.commit()
            return request_id
            
        except Exception as e:
            self.db.execute("ROLLBACK")
            logger.error(f"Error creating purchase request: {e}")
            return None
            
    def get_purchase_request(self, request_id: int) -> Optional[Dict[str, Any]]:
        """Get purchase request details"""
        try:
            self.db.execute("""
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
            result = self.db.cur.fetchone()
            
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
            logger.error(f"Error getting purchase request: {e}")
            return None
            
    def get_pending_requests(self) -> List[Tuple]:
        """Get all pending purchase requests"""
        try:
            self.db.execute("""
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
            return self.db.cur.fetchall()
        except Exception as e:
            logger.error(f"Error getting pending requests: {e}")
            return []
            
    def update_request_status(self, request_id: int, status: str) -> bool:
        """Update purchase request status"""
        try:
            # Get user_id from purchase request
            self.db.execute(
                "SELECT user_id FROM purchase_requests WHERE id = ?",
                (request_id,)
            )
            result = self.db.cur.fetchone()
            if not result:
                logger.error(f"Purchase request #{request_id} not found")
                return False
            
            user_id = result[0]
            
            # If status is rejected, increment failed_payments
            if status == 'rejected':
                self.db.execute(
                    """UPDATE users 
                       SET failed_payments = failed_payments + 1 
                       WHERE telegram_id = ?""",
                    (user_id,)
                )
                
                # Check if user should be banned
                self.db.execute(
                    """SELECT failed_payments 
                       FROM users 
                       WHERE telegram_id = ?""",
                    (user_id,)
                )
                failed_payments = self.db.cur.fetchone()[0]
                
                if failed_payments >= 3:
                    self.db.execute(
                        """UPDATE users 
                           SET is_banned = 1 
                           WHERE telegram_id = ?""",
                        (user_id,)
                    )
                    logger.warning(f"User {user_id} has been banned due to too many failed payments")
            
            # If status is completed, reset failed_payments
            elif status == 'completed':
                self.db.execute(
                    """UPDATE users 
                       SET failed_payments = 0 
                       WHERE telegram_id = ?""",
                    (user_id,)
                )
            
            self.db.execute(
                """UPDATE purchase_requests 
                   SET status = ?, updated_at = CURRENT_TIMESTAMP 
                   WHERE id = ?""",
                (status, request_id)
            )
            self.db.commit()
            logger.info(f"Successfully updated request #{request_id} status")
            return True
        except Exception as e:
            logger.exception(f"Error updating purchase request #{request_id}: {str(e)}")
            return False
            
    def get_user_orders(self, user_id: int, status: Optional[str] = None) -> List[Tuple]:
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
                WHERE pr.user_id = ?
            """
            
            params = [user_id]
            if status:
                query += " AND pr.status = ?"
                params.append(status)
                
            query += " GROUP BY pr.id ORDER BY pr.created_at DESC"
            
            self.db.execute(query, tuple(params))
            return self.db.cur.fetchall()
        except Exception as e:
            logger.error(f"Error getting user orders: {e}")
            return []
            
    def get_user_active_request(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user's active (pending) purchase request"""
        try:
            self.db.execute("""
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
            result = self.db.cur.fetchone()
            
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
            
    def get_order_stats(self, order_id: int) -> Dict[str, Any]:
        """Get detailed statistics for an order"""
        try:
            stats = {}
            
            # Basic order info
            self.db.execute("""
                SELECT 
                    pr.*,
                    u.failed_payments,
                    u.is_banned,
                    COUNT(DISTINCT pri.id) as total_items,
                    SUM(pri.quantity) as total_quantity
                FROM purchase_requests pr
                JOIN users u ON pr.user_id = u.telegram_id
                JOIN purchase_request_items pri ON pr.id = pri.request_id
                WHERE pr.id = ?
                GROUP BY pr.id
            """, (order_id,))
            
            result = self.db.cur.fetchone()
            if not result:
                return {}
                
            stats.update({
                'id': result[0],
                'user_id': result[1],
                'total_amount': result[2],
                'wallet': result[3],
                'status': result[4],
                'created_at': result[5],
                'updated_at': result[6],
                'user_failed_payments': result[7],
                'user_is_banned': result[8],
                'total_items': result[9],
                'total_quantity': result[10]
            })
            
            # Calculate processing time
            if stats['updated_at'] and stats['created_at']:
                created = datetime.strptime(stats['created_at'], '%Y-%m-%d %H:%M:%S')
                updated = datetime.strptime(stats['updated_at'], '%Y-%m-%d %H:%M:%S')
                processing_time = updated - created
                stats['processing_time'] = str(processing_time)
            else:
                stats['processing_time'] = 'N/A'
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting order stats: {e}")
            return {}