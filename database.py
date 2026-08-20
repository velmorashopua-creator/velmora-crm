import os
import json
import gspread
from google.oauth2.service_account import Credentials
from config import SPREADSHEET_NAME

def get_google_sheet(worksheet_name="Замовлення"):
    """
    Універсальна функція для підключення до потрібного аркуша таблиці.
    За замовчуванням відкриває 'Замовлення'.
    """
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    creds_dict = json.loads(creds_json)
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(credentials)
    
    # Відкриваємо таблицю за назвою з config.py і вибираємо конкретний аркуш
    return client.open(SPREADSHEET_NAME).worksheet(worksheet_name)

def save_order_to_sheet(order_data: dict):
    """
    Збереження нового замовлення.
    """
    sheet = get_google_sheet("Замовлення")
    row = [
        order_data.get("date", ""),
        order_data.get("name", ""),
        order_data.get("phone", ""),
        order_data.get("pet", ""),
        order_data.get("city", ""),
        order_data.get("warehouse", ""),
        order_data.get("product", ""),
        order_data.get("status", "Новий"),
        "" # 9-та колонка для номера ТТН, залишається порожньою при створенні
    ]
    sheet.append_row(row)

def update_order_in_sheet(row_number: int, status: str, ttn: str):
    """
    Оновлення статусу та ТТН в існуючому замовленні.
    """
    sheet = get_google_sheet("Замовлення")
    # Статус у 8-й колонці (H), ТТН — у 9-й (I)
    sheet.update_cell(row_number, 8, status)
    sheet.update_cell(row_number, 9, ttn)

def add_prichid_bulk(rows_data: list):
    """
    Масове збереження всіх товарів з прибуткової накладної (оптом за 1 запит).
    Відправляє дані на аркуш 'Прихід'.
    """
    sheet = get_google_sheet("Прихід")
    sheet.append_rows(rows_data)

def add_vydatky(data: dict):
    """
    Фіксація операційних витрат (логістика, реклама, оренда тощо).
    Відправляє дані на аркуш 'Видатки'.
    """
    sheet = get_google_sheet("Видатки")
    row = [
        data.get("date", ""),
        data.get("category", ""),
        data.get("sum", ""),
        data.get("comment", ""),
        data.get("order_id", "")
    ]
    sheet.append_row(row)
