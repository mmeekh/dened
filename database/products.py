from typing import Optional, List, Tuple, Dict, Any
from .core import Database
import logging

logger = logging.getLogger(__name__)

class ProductsDB:
    def __init__(self, db: Database):
        self.db = db
        
    def add_product(self, name: str, description: str, price: float, 
                   image_path: str, stock: int = 0) -> bool:
        """Add a new product"""
        try:
            self.db.execute(
                """INSERT INTO products
                   (name, description, price, image_path, stock) 
                   VALUES (?, ?, ?, ?, ?)""",
                (name, description, price, image_path, stock)
            )
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding product: {e}")
            return False
            
        
    def update_product_stock(self, product_id: int, quantity: int) -> bool:
        """Update product stock"""
        try:
            self.db.execute(
                "UPDATE products SET stock = stock + ? WHERE id = ?",
                (quantity, product_id)
            )
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating stock: {e}")
            return False

    def update_product(self, product_id: int, **kwargs) -> bool:
        """Update product fields"""
        valid_fields = {'name', 'description', 'price', 'image_path', 
                       'stock', 'sort_order'}
        update_fields = {k: v for k, v in kwargs.items() if k in valid_fields}
        
        if not update_fields:
            return False
            
        query = "UPDATE products SET "
        query += ", ".join(f"{k} = ?" for k in update_fields.keys())
        query += " WHERE id = ?"
        
        try:
            self.db.execute(query, (*update_fields.values(), product_id))
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating product: {e}")
            return False
            
    def get_product(self, product_id: int) -> Optional[Tuple]:
        """Get product by ID"""
        result = self.db.execute(
            "SELECT * FROM products WHERE id = ?",
            (product_id,)
        )
        return result[0] if result else None
        
    def delete_product(self, product_id: int) -> bool:
        """Delete a product"""
        try:
            self.db.execute("DELETE FROM products WHERE id = ?", (product_id,))
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting product: {e}")
            return False
            
    def get_product_stats(self, product_id: int) -> Dict[str, Any]:
        """Get detailed statistics for a product"""
        try:
            stats = {}
            
            # Basic product info
            product = self.get_product(product_id)
            if not product:
                return {}
                
            stats.update({
                'id': product[0],
                'name': product[1],
                'price': product[3],
                'stock': product[5]
            })
            
            # Sales statistics
            self.db.execute("""
                SELECT 
                    COUNT(DISTINCT pr.id) as total_orders,
                    SUM(pri.quantity) as total_quantity,
                    SUM(pri.quantity * pri.price) as total_revenue,
                    AVG(pri.price) as avg_price
                FROM purchase_request_items pri
                JOIN purchase_requests pr ON pri.request_id = pr.id
                WHERE pri.product_id = ? AND pr.status = 'completed'
            """, (product_id,))
            
            sales = self.db.cur.fetchone()
            stats.update({
                'total_orders': sales[0] if sales[0] else 0,
                'total_quantity': sales[1] if sales[1] else 0,
                'total_revenue': sales[2] if sales[2] else 0,
                'avg_price': round(sales[3], 2) if sales[3] else 0
            })
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting product stats: {e}")
            return {}