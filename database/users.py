from typing import Optional, List, Tuple
from .core import Database

class UsersDB:
    def __init__(self, db: Database):
        self.db = db
        
    def add_user(self, telegram_id: int) -> bool:
        """Add new user if not exists"""
        try:
            self.db.execute(
                """INSERT OR IGNORE INTO users (telegram_id, failed_payments, is_banned) 
                   VALUES (?, 0, 0)""",
                (telegram_id,)
            )
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return False
            
    def get_user(self, telegram_id: int) -> Optional[Tuple]:
        """Get user by telegram ID"""
        result = self.db.execute(
            "SELECT * FROM users WHERE telegram_id = ?",
            (telegram_id,)
        )
        return result[0] if result else None
        
    def get_all_users(self) -> List[Tuple]:
        """Get all users"""
        result = self.db.execute("SELECT * FROM users")
        return result if result else []
        
    def update_user(self, telegram_id: int, **kwargs) -> bool:
        """Update user fields"""
        valid_fields = {'failed_payments', 'is_banned'}
        update_fields = {k: v for k, v in kwargs.items() if k in valid_fields}
        
        if not update_fields:
            return False
            
        query = "UPDATE users SET "
        query += ", ".join(f"{k} = ?" for k in update_fields.keys())
        query += " WHERE telegram_id = ?"
        
        try:
            self.db.execute(query, (*update_fields.values(), telegram_id))
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return False