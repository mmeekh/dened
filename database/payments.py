from typing import Dict, Any, Optional, List, Tuple
from .core import Database
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class PaymentsDB:
    def __init__(self, db: Database):
        self.db = db
        
    def create_payment(self, user_id: int, amount: float, wallet: str) -> Optional[int]:
        """Create a new payment record"""
        try:
            self.db.execute(
                """INSERT INTO payments 
                   (user_id, amount, wallet, status) 
                   VALUES (?, ?, ?, 'pending')""",
                (user_id, amount, wallet)
            )
            self.db.commit()
            return self.db.cur.lastrowid
        except Exception as e:
            logger.error(f"Error creating payment: {e}")
            return None
            
    def get_payment(self, payment_id: int) -> Optional[Dict[str, Any]]:
        """Get payment details"""
        try:
            self.db.execute(
                "SELECT * FROM payments WHERE id = ?",
                (payment_id,)
            )
            result = self.db.cur.fetchone()
            if result:
                return {
                    'id': result[0],
                    'user_id': result[1],
                    'amount': result[2],
                    'wallet': result[3],
                    'status': result[4],
                    'created_at': result[5],
                    'updated_at': result[6]
                }
            return None
        except Exception as e:
            logger.error(f"Error getting payment: {e}")
            return None
            
    def update_payment_status(self, payment_id: int, status: str) -> bool:
        """Update payment status"""
        try:
            self.db.execute(
                """UPDATE payments 
                   SET status = ?, updated_at = CURRENT_TIMESTAMP 
                   WHERE id = ?""",
                (status, payment_id)
            )
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating payment status: {e}")
            return False
            
    def get_user_payments(self, user_id: int, status: Optional[str] = None) -> List[Tuple]:
        """Get user's payments filtered by status"""
        try:
            query = "SELECT * FROM payments WHERE user_id = ?"
            params = [user_id]
            
            if status:
                query += " AND status = ?"
                params.append(status)
                
            query += " ORDER BY created_at DESC"
            
            self.db.execute(query, tuple(params))
            return self.db.cur.fetchall()
        except Exception as e:
            logger.error(f"Error getting user payments: {e}")
            return []
            
    def get_payment_stats(self, payment_id: int) -> Dict[str, Any]:
        """Get detailed statistics for a payment"""
        try:
            stats = {}
            
            # Basic payment info
            payment = self.get_payment(payment_id)
            if not payment:
                return {}
                
            stats.update(payment)
            
            # Calculate processing time
            if payment['updated_at'] and payment['created_at']:
                created = datetime.strptime(payment['created_at'], '%Y-%m-%d %H:%M:%S')
                updated = datetime.strptime(payment['updated_at'], '%Y-%m-%d %H:%M:%S')
                processing_time = updated - created
                stats['processing_time'] = str(processing_time)
            else:
                stats['processing_time'] = 'N/A'
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting payment stats: {e}")
            return {}