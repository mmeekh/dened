#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Oyun skorlarını manuel olarak sıfırlamak için kullanılan komut satırı aracı.
Kullanım:
    python reset_scores.py [--user_id USER_ID] [--confirm]

Seçenekler:
    --user_id USER_ID    Belirli bir kullanıcının skorlarını sıfırla
    --confirm            Onay istemeden doğrudan sıfırla
"""

import sqlite3
import argparse
import sys
import logging
from datetime import datetime

# Logging ayarlamaları
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('score_reset.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("score_reset")

def connect_to_db(db_name="shop.db"):
    """Veritabanına bağlanır"""
    try:
        conn = sqlite3.connect(db_name)
        return conn
    except sqlite3.Error as e:
        logger.error(f"Veritabanına bağlanırken hata: {e}")
        sys.exit(1)

def reset_all_scores(conn, confirm=False):
    """Tüm oyun skorlarını sıfırlar"""
    if not confirm:
        response = input("⚠️ TÜM OYUN SKORLARI SIFIRLANACAK! Devam etmek istiyor musunuz? (e/h): ")
        if response.lower() not in ["e", "evet", "y", "yes"]:
            logger.info("İşlem kullanıcı tarafından iptal edildi.")
            return False

    cursor = conn.cursor()
    
    try:
        # Mevcut skorları say
        cursor.execute("SELECT COUNT(*) FROM game_scores")
        count = cursor.fetchone()[0]
        
        # Yedek tablo oluştur
        backup_table_name = f"game_scores_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        cursor.execute(f"CREATE TABLE {backup_table_name} AS SELECT * FROM game_scores")
        
        # Skorları sıfırla
        cursor.execute("DELETE FROM game_scores")
        conn.commit()
        
        logger.info(f"✅ Toplam {count} skor başarıyla sıfırlandı!")
        logger.info(f"📋 Yedek tablo oluşturuldu: {backup_table_name}")
        return True
    except sqlite3.Error as e:
        logger.error(f"Skorlar sıfırlanırken hata: {e}")
        conn.rollback()
        return False

def reset_user_scores(conn, user_id, confirm=False):
    """Belirli bir kullanıcının skorlarını sıfırlar"""
    if not confirm:
        response = input(f"⚠️ KULLANICI {user_id} SKORLARI SIFIRLANACAK! Devam etmek istiyor musunuz? (e/h): ")
        if response.lower() not in ["e", "evet", "y", "yes"]:
            logger.info("İşlem kullanıcı tarafından iptal edildi.")
            return False

    cursor = conn.cursor()
    
    try:
        # Kullanıcının skorlarını say
        cursor.execute("SELECT COUNT(*) FROM game_scores WHERE user_id = ?", (user_id,))
        count = cursor.fetchone()[0]
        
        if count == 0:
            logger.info(f"⚠️ Kullanıcı {user_id} için hiç skor bulunamadı.")
            return False
        
        # Yedek tablo oluştur
        backup_table_name = f"user_{user_id}_scores_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        cursor.execute(f"CREATE TABLE {backup_table_name} AS SELECT * FROM game_scores WHERE user_id = ?", (user_id,))
        
        # Kullanıcının skorlarını sıfırla
        cursor.execute("DELETE FROM game_scores WHERE user_id = ?", (user_id,))
        conn.commit()
        
        logger.info(f"✅ Kullanıcı {user_id} için toplam {count} skor başarıyla sıfırlandı!")
        logger.info(f"📋 Yedek tablo oluşturuldu: {backup_table_name}")
        return True
    except sqlite3.Error as e:
        logger.error(f"Kullanıcı skorları sıfırlanırken hata: {e}")
        conn.rollback()
        return False

def show_top_users(conn):
    """En yüksek toplam puanı olan kullanıcıları gösterir"""
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT user_id, SUM(score) as total_score, MAX(score) as best_score, COUNT(*) as games_played
            FROM game_scores
            GROUP BY user_id
            ORDER BY total_score DESC
            LIMIT 10
        """)
        users = cursor.fetchall()
        
        if not users:
            print("⚠️ Hiç oyun skoru bulunamadı.")
            return
        
        print("\n📊 En Yüksek Puanlı Kullanıcılar:")
        print("-" * 80)
        print(f"{'Kullanıcı ID':<12} {'Toplam Puan':<15} {'En Yüksek Skor':<15} {'Oyun Sayısı':<15}")
        print("-" * 80)
        
        for user in users:
            print(f"{user[0]:<12} {user[1]:<15} {user[2]:<15} {user[3]:<15}")
        
        print("-" * 80)
        
    except sqlite3.Error as e:
        logger.error(f"Kullanıcı bilgileri getirilirken hata: {e}")

def restore_backup(conn, table_name):
    """Yedek tablodan verileri geri yükler"""
    cursor = conn.cursor()
    
    try:
        # Yedek tablo var mı kontrol et
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        if not cursor.fetchone():
            logger.error(f"⚠️ Yedek tablo '{table_name}' bulunamadı!")
            return False
        
        # Mevcut skorları temizle (eğer belirli bir kullanıcı yedeği ise sadece o kullanıcıyı temizle)
        if table_name.startswith("user_"):
            user_id = table_name.split("_")[1]
            cursor.execute("DELETE FROM game_scores WHERE user_id = ?", (user_id,))
        else:
            cursor.execute("DELETE FROM game_scores")
        
        # Yedekten verileri geri yükle
        cursor.execute(f"INSERT INTO game_scores SELECT * FROM {table_name}")
        
        # Etkilenen satır sayısı
        row_count = cursor.rowcount
        conn.commit()
        
        logger.info(f"✅ {row_count} satır '{table_name}' tablosundan başarıyla geri yüklendi!")
        return True
    except sqlite3.Error as e:
        logger.error(f"Yedek geri yüklenirken hata: {e}")
        conn.rollback()
        return False

def list_backups(conn):
    """Mevcut yedek tabloları listeler"""
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%game_scores_backup_%' OR name LIKE '%scores_backup_%'")
        backups = cursor.fetchall()
        
        if not backups:
            print("⚠️ Hiç yedek tablo bulunamadı.")
            return []
        
        print("\n📋 Mevcut Yedek Tablolar:")
        print("-" * 80)
        
        backup_list = []
        for i, backup in enumerate(backups, 1):
            backup_name = backup[0]
            backup_list.append(backup_name)
            print(f"{i}. {backup_name}")
        
        print("-" * 80)
        return backup_list
        
    except sqlite3.Error as e:
        logger.error(f"Yedek tabloları listelerken hata: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description="Oyun skorlarını sıfırlama aracı")
    parser.add_argument("--user_id", type=int, help="Belirli bir kullanıcının skorlarını sıfırla")
    parser.add_argument("--confirm", action="store_true", help="Onay istemeden doğrudan sıfırla")
    parser.add_argument("--list", action="store_true", help="En yüksek puanlı kullanıcıları göster")
    parser.add_argument("--backups", action="store_true", help="Yedek tabloları listele")
    parser.add_argument("--restore", type=str, help="Belirtilen yedek tabloyu geri yükle")
    
    args = parser.parse_args()
    
    conn = connect_to_db()
    
    try:
        if args.list:
            show_top_users(conn)
            return
            
        if args.backups:
            list_backups(conn)
            return
            
        if args.restore:
            restore_backup(conn, args.restore)
            return
            
        if args.user_id:
            reset_user_scores(conn, args.user_id, args.confirm)
        else:
            # Yedekleri göster
            backups = list_backups(conn)
            # Kullanıcı bilgilerini göster
            show_top_users(conn)
            # Tüm skorları sıfırla
            reset_all_scores(conn, args.confirm)
    finally:
        conn.close()

if __name__ == "__main__":
    main()