import sqlite3

# Veritabanına bağlan
conn = sqlite3.connect('shop.db')
cursor = conn.cursor()

# Tüm cüzdanları kullanılabilir olarak işaretle
cursor.execute("UPDATE wallets SET in_use = 0")
conn.commit()

# Veritabanını kapat
conn.close()

print("Tüm cüzdanlar sıfırlandı")