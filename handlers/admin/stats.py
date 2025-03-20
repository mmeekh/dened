import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import Database
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
db = Database('shop.db')

async def show_stats_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show statistics menu"""
    keyboard = [
        [
            InlineKeyboardButton("📊 Genel İstatistikler", callback_data='general_stats'),
            InlineKeyboardButton("💰 Satış İstatistikleri", callback_data='sales_stats')
        ],
        [
            InlineKeyboardButton("👥 Kullanıcı Analizi", callback_data='user_stats'),
            InlineKeyboardButton("📈 Performans Raporu", callback_data='performance_stats')
        ],
        [InlineKeyboardButton("🔙 Ana Menü", callback_data='main_menu')]
    ]
    
    message = """📊 İstatistik Menüsü

İncelemek istediğiniz istatistik türünü seçin:

📊 Genel İstatistikler
• Toplam kullanıcı, sipariş ve gelir
• Başarı ve onay oranları
• Genel sistem durumu

💰 Satış İstatistikleri
• Günlük/haftalık/aylık satışlar
• En çok satan ürünler
• Ortalama sipariş tutarı

👥 Kullanıcı Analizi
• Aktif kullanıcılar
• Yasaklı kullanıcılar
• Kullanıcı davranışları

📈 Performans Raporu
• Ortalama onay süresi
• Başarı oranları
• Sistem performansı"""
    
    await update.callback_query.message.edit_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_general_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show general statistics"""
    try:
        stats = db.get_general_stats()
        
        message = """📊 Genel İstatistikler

👥 Kullanıcılar:
• Toplam: {total_users:,}
• Yasaklı: {banned_users:,}
• Son 24 Saat: +{new_users_24h:,}
• 7 Gün Aktif: {active_users_7d:,}

🛍️ Siparişler:
• Toplam: {total_orders:,}
• Tamamlanan: {completed_orders:,}
• Reddedilen: {rejected_orders:,}
• Bekleyen: {pending_orders:,}

💰 Finansal:
• Toplam Gelir: {total_revenue:,.2f} USDT
• Ortalama Sipariş: {avg_order_value:,.2f} USDT
• En Yüksek Sipariş: {max_order_value:,.2f} USDT

📊 Oranlar:
• Onay Oranı: %{approval_rate:.1f}
• Başarı Oranı: %{success_rate:.1f}
• Ortalama Onay: {avg_approval_time}

👛 Cüzdanlar:
• Toplam: {total_wallets:,}
• Kullanımda: {in_use_wallets:,}
• Müsait: {available_wallets:,}""".format(**stats)

        keyboard = [
            [InlineKeyboardButton("🔄 Yenile", callback_data='general_stats')],
            [InlineKeyboardButton("🔙 İstatistik Menüsü", callback_data='stats_menu')]
        ]
        
        await update.callback_query.message.edit_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing general stats: {e}")
        await update.callback_query.message.edit_text(
            "❌ İstatistikler yüklenirken bir hata oluştu.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 İstatistik Menüsü", callback_data='stats_menu')
            ]])
        )

async def show_sales_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show sales statistics"""
    try:
        stats = db.get_sales_stats()
        
        message = """💰 Satış İstatistikleri

📅 Günlük:
• Siparişler: {daily_orders:,}
• Tamamlanan: {daily_completed:,}
• Reddedilen: {daily_rejected:,}
• Gelir: {daily_revenue:,.2f} USDT

📅 Haftalık:
• Siparişler: {weekly_orders:,}
• Tamamlanan: {weekly_completed:,}
• Reddedilen: {weekly_rejected:,}
• Gelir: {weekly_revenue:,.2f} USDT

📅 Aylık:
• Siparişler: {monthly_orders:,}
• Tamamlanan: {monthly_completed:,}
• Reddedilen: {monthly_rejected:,}
• Gelir: {monthly_revenue:,.2f} USDT

📈 Trend:
• Günlük Ortalama: {daily_avg:,.2f} USDT
• Haftalık Ortalama: {weekly_avg:,.2f} USDT
• Aylık Ortalama: {monthly_avg:,.2f} USDT""".format(**stats)

        keyboard = [
            [InlineKeyboardButton("🔄 Yenile", callback_data='sales_stats')],
            [InlineKeyboardButton("🔙 İstatistik Menüsü", callback_data='stats_menu')]
        ]
        
        await update.callback_query.message.edit_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing sales stats: {e}")
        await update.callback_query.message.edit_text(
            "❌ Satış istatistikleri yüklenirken bir hata oluştu.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 İstatistik Menüsü", callback_data='stats_menu')
            ]])
        )

async def show_user_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user statistics"""
    try:
        stats = db.get_user_stats()
        
        message = """👥 Kullanıcı İstatistikleri

📊 Genel Durum:
• Toplam Kullanıcı: {total_users:,}
• Aktif Kullanıcı: {active_users:,}
• Yasaklı: {banned_users:,}
• Risk Altında: {at_risk_users:,}

📅 Aktivite:
• Bugün Aktif: {today_active:,}
• Bu Hafta Aktif: {week_active:,}
• Bu Ay Aktif: {month_active:,}

🔄 Dönüşüm:
• Sipariş Yapan: {users_with_orders:,}
• Tekrar Eden: {returning_users:,}
• Dönüşüm Oranı: %{conversion_rate:.1f}

⚠️ Risk Analizi:
• 1 Başarısız: {one_failed:,}
• 2 Başarısız: {two_failed:,}
• Yasaklananlar: {banned_today:,} (bugün)""".format(**stats)

        keyboard = [
            [InlineKeyboardButton("🔄 Yenile", callback_data='user_stats')],
            [InlineKeyboardButton("🔙 İstatistik Menüsü", callback_data='stats_menu')]
        ]
        
        await update.callback_query.message.edit_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing user stats: {e}")
        await update.callback_query.message.edit_text(
            "❌ Kullanıcı istatistikleri yüklenirken bir hata oluştu.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 İstatistik Menüsü", callback_data='stats_menu')
            ]])
        )

async def show_performance_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show performance statistics"""
    try:
        stats = db.get_performance_stats()
        
        message = """📈 Performans Raporu

⏱️ Onay Süreleri:
• Ortalama: {avg_approval_time}
• En Hızlı: {min_approval_time}
• En Yavaş: {max_approval_time}

📊 Başarı Oranları:
• Onay Oranı: %{approval_rate:.1f}
• Red Oranı: %{rejection_rate:.1f}
• İptal Oranı: %{cancellation_rate:.1f}

💰 İşlem Analizi:
• Toplam İşlem: {total_volume:,.2f} USDT
• Ortalama İşlem: {avg_transaction:,.2f} USDT
• Başarılı İşlem: {successful_transactions:,}

⚡️ Sistem Durumu:
• Aktif Cüzdanlar: {active_wallets:,}
• Bekleyen İşlemler: {pending_transactions:,}
• Yük Durumu: %{system_load:.1f}""".format(**stats)

        keyboard = [
            [InlineKeyboardButton("🔄 Yenile", callback_data='performance_stats')],
            [InlineKeyboardButton("🔙 İstatistik Menüsü", callback_data='stats_menu')]
        ]
        
        await update.callback_query.message.edit_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing performance stats: {e}")
        await update.callback_query.message.edit_text(
            "❌ Performans istatistikleri yüklenirken bir hata oluştu.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 İstatistik Menüsü", callback_data='stats_menu')
            ]])
        )