from typing import Optional, List, Tuple
from .core import Database
import logging
logger = logging.getLogger(__name__)

class WalletsDB:
    def __init__(self, db: Database):
        self.db = db
        
    def add_wallet(self, address: str) -> bool:
        """Add a new wallet to the pool"""
        try:
            self.db.execute(
                "INSERT INTO wallets (address, in_use) VALUES (?, 0)",
                (address,)
            )
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding wallet: {e}")
            return False
            
    def get_available_wallet(self) -> Optional[str]:
        """Get an available wallet and mark it as in use"""
        try:
            result = self.db.execute(
                "SELECT address FROM wallets WHERE in_use = 0 LIMIT 1"
            )
            if not result:
                return None
                
            address = result[0][0]
            self.db.execute(
                "UPDATE wallets SET in_use = 1 WHERE address = ?",
                (address,)
            )
            self.db.commit()
            return address
        except Exception as e:
            logger.error(f"Error getting available wallet: {e}")
            return None
            
    def release_wallet(self, address: str) -> bool:
        """Mark a wallet as available"""
        try:
            self.db.execute(
                "UPDATE wallets SET in_use = 0 WHERE address = ?",
                (address,)
            )
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error releasing wallet: {e}")
            return False
            
    def get_all_wallets(self) -> List[Tuple]:
        """Get all wallets"""
        result = self.db.execute(
            """
            SELECT w.*, 
                COUNT(DISTINCT CASE WHEN pr.status = 'completed' THEN pr.id END) as completed_txns,
                SUM(CASE WHEN pr.status = 'completed' THEN pr.total_amount ELSE 0 END) as total_volume,
                MAX(pr.created_at) as last_used
            FROM wallets w
            LEFT JOIN purchase_requests pr ON w.address = pr.wallet
            GROUP BY w.id, w.address, w.in_use
            ORDER BY w.in_use ASC, last_used DESC
            """
        )
        return result if result else []

    def get_wallet_stats(self, wallet_id: int) -> Optional[Tuple]:
        """Get detailed statistics for a wallet"""
        result = self.db.execute(
            """
            SELECT 
                w.*,
                COUNT(DISTINCT pr.id) as total_txns,
                COUNT(DISTINCT CASE WHEN pr.status = 'completed' THEN pr.id END) as completed_txns,
                COUNT(DISTINCT CASE WHEN pr.status = 'rejected' THEN pr.id END) as rejected_txns,
                SUM(CASE WHEN pr.status = 'completed' THEN pr.total_amount ELSE 0 END) as total_volume,
                MAX(pr.created_at) as last_used
            FROM wallets w
            LEFT JOIN purchase_requests pr ON w.address = pr.wallet
            WHERE w.id = ?
            GROUP BY w.id, w.address, w.in_use
            """,
            (wallet_id,)
        )
        return result[0] if result else None

    def rotate_wallets(self) -> bool:
        """Automatically rotate wallets to distribute load"""
        try:
            # Mark old wallets as available if no pending transactions
            self.db.execute(
                """
                UPDATE wallets w
                SET in_use = 0
                WHERE in_use = 1
                AND NOT EXISTS (
                    SELECT 1 FROM purchase_requests pr
                    WHERE pr.wallet = w.address
                    AND pr.status = 'pending'
                )
                """
            )
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error rotating wallets: {e}")
            return False
        
    def delete_wallet(self, wallet_id: int) -> bool:
        """Delete an unused wallet"""
        try:
            self.db.execute(
                "DELETE FROM wallets WHERE id = ? AND in_use = 0",
                (wallet_id,)
            )
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting wallet: {e}")
            return False