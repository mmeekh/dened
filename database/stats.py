from typing import Dict, Any
from .core import Database
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class StatsDB:
    def __init__(self, db: Database):
        self.db = db
        
    def get_user_stats(self) -> Dict[str, Any]:
        """Get detailed user statistics"""
        try:
            stats = {}
            
            # Basic user counts
            self.db.execute("""
                SELECT 
                    COUNT(*) as total_users,
                    SUM(CASE WHEN is_banned = 1 THEN 1 ELSE 0 END) as banned_users,
                    SUM(CASE WHEN failed_payments = 1 THEN 1 ELSE 0 END) as one_failed,
                    SUM(CASE WHEN failed_payments = 2 THEN 1 ELSE 0 END) as two_failed
                FROM users
            """)
            result = self.db.cur.fetchone()
            stats.update({
                'total_users': result[0],
                'banned_users': result[1],
                'one_failed': result[2],
                'two_failed': result[3],
                'at_risk_users': result[2] + result[3]
            })
            
            # Active users
            self.db.execute("""
                SELECT 
                    COUNT(DISTINCT user_id) as today_active,
                    COUNT(DISTINCT CASE 
                        WHEN created_at >= datetime('now', '-7 days') 
                        THEN user_id END) as week_active,
                    COUNT(DISTINCT CASE 
                        WHEN created_at >= datetime('now', '-30 days') 
                        THEN user_id END) as month_active
                FROM purchase_requests
                WHERE created_at >= datetime('now', '-1 day')
            """)
            result = self.db.cur.fetchone()
            stats.update({
                'today_active': result[0],
                'week_active': result[1],
                'month_active': result[2]
            })
            
            # User conversion
            self.db.execute("""
                SELECT 
                    COUNT(DISTINCT user_id) as users_with_orders,
                    COUNT(DISTINCT CASE 
                        WHEN status = 'completed' 
                        THEN user_id END) as successful_users,
                    COUNT(DISTINCT CASE 
                        WHEN user_id IN (
                            SELECT user_id 
                            FROM purchase_requests 
                            WHERE status = 'completed' 
                            GROUP BY user_id 
                            HAVING COUNT(*) > 1
                        ) THEN user_id END) as returning_users
                FROM purchase_requests
            """)
            result = self.db.cur.fetchone()
            stats.update({
                'users_with_orders': result[0],
                'successful_users': result[1],
                'returning_users': result[2]
            })
            
            # Calculate conversion rate
            stats['conversion_rate'] = (
                (stats['successful_users'] / stats['total_users'] * 100)
                if stats['total_users'] > 0 else 0
            )
            
            # Today's bans
            self.db.execute("""
                SELECT COUNT(*) 
                FROM users 
                WHERE is_banned = 1 
                AND created_at >= datetime('now', '-1 day')
            """)
            stats['banned_today'] = self.db.cur.fetchone()[0]
            
            # Calculate active users
            stats['active_users'] = stats['total_users'] - stats['banned_users']
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {}
            
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get system performance statistics"""
        try:
            stats = {}
            
            # Processing times
            self.db.execute("""
                SELECT 
                    AVG(CAST(
                        (JULIANDAY(updated_at) - JULIANDAY(created_at)) * 24 * 60 
                    AS INTEGER)) as avg_time,
                    MIN(CAST(
                        (JULIANDAY(updated_at) - JULIANDAY(created_at)) * 24 * 60 
                    AS INTEGER)) as min_time,
                    MAX(CAST(
                        (JULIANDAY(updated_at) - JULIANDAY(created_at)) * 24 * 60 
                    AS INTEGER)) as max_time
                FROM purchase_requests
                WHERE status IN ('completed', 'rejected')
            """)
            result = self.db.cur.fetchone()
            
            stats.update({
                'avg_approval_time': f"{int(result[0])} dakika" if result[0] else "N/A",
                'min_approval_time': f"{int(result[1])} dakika" if result[1] else "N/A",
                'max_approval_time': f"{int(result[2])} dakika" if result[2] else "N/A"
            })
            
            # Success rates
            self.db.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected
                FROM purchase_requests
                WHERE status != 'pending'
            """)
            result = self.db.cur.fetchone()
            total = result[0] if result[0] > 0 else 1
            
            stats.update({
                'approval_rate': (result[1] / total * 100),
                'rejection_rate': (result[2] / total * 100),
                'cancellation_rate': 0  # Placeholder for future feature
            })
            
            # Transaction analysis
            self.db.execute("""
                SELECT 
                    COUNT(*) as total_txns,
                    SUM(total_amount) as total_volume,
                    AVG(total_amount) as avg_amount
                FROM purchase_requests
                WHERE status = 'completed'
            """)
            result = self.db.cur.fetchone()
            
            stats.update({
                'successful_transactions': result[0],
                'total_volume': result[1] if result[1] else 0,
                'avg_transaction': result[2] if result[2] else 0
            })
            
            # System status
            self.db.execute("""
                SELECT 
                    COUNT(*) as pending,
                    COUNT(DISTINCT wallet) as active_wallets
                FROM purchase_requests
                WHERE status = 'pending'
            """)
            result = self.db.cur.fetchone()
            
            stats.update({
                'pending_transactions': result[0],
                'active_wallets': result[1],
                'system_load': (result[0] / 10 * 100) if result[0] > 0 else 0  # Example load calculation
            })
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting performance stats: {e}")
            return {}