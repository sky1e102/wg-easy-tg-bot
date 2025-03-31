from dotenv import load_dotenv
import os

load_dotenv("config.env")

TELEGRAM_TOKEN = "ВАШ_ТОКЕН_ЗДЕСЬ"  # Замените на ваш токен Telegram
WG_CONFIG_PATH = "ВАШ_ПУТЬ_К_WG_CONFIG"  # Замените на путь к вашему конфигу WireGuard
ADMIN_IDS = [7103101829]  # Замените на реальные Telegram ID администраторов