import os
import json
import gspread
from google.oauth2.service_account import Credentials
from config import SPREADSHEET_NAME

def get_google_sheet(worksheet_name="Замовлення"):
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    creds_dict = json.loads(creds_json)
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(credentials)
    return client.open(SPREADSHEET_NAME).worksheet(worksheet_name)

def save_order_to_sheet(order_data: dict):
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
        "" # ТТН
    ]
    sheet.append_row(row)

def update_order_in_sheet(row_number: int, status: str, ttn: str):
    sheet = get_google_sheet("Замовлення")
    sheet.update_cell(row_number, 8, status)
    sheet.update_cell(row_number, 9, ttn)

# Функции для учета (Приход, Витрати, Видатки)
def add_prichid(data: dict):
    sheet = get_google_sheet("Прихід")
    row = [
        data.get("date", ""),
        data.get("article", ""),
        data.get("name", ""),
        data.get("qty", ""),
        data.get("total_sum", ""),
        data.get("supplier", ""),
        data.get("unit_cost", "")
    ]
    sheet.append_row(row)

def add_vydatky(data: dict):
    sheet = get_google_sheet("Видатки")
    row = [
        data.get("date", ""),
        data.get("category", ""),
        data.get("sum", ""),
        data.get("comment", ""),
        data.get("order_id", "")
    ]
    sheet.append_row(row)
