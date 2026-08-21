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

def add_prichid_bulk(rows_data: list):
    sheet = get_google_sheet("Прихід")
    sheet.append_rows(rows_data)

def add_vitraty_bulk(rows_data: list):
    sheet = get_google_sheet("Витрати")
    sheet.append_rows(rows_data)

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

def get_specs_from_sheet():
    """Читає лист Спеціфікація та формує техкарти боксів"""
    try:
        sheet = get_google_sheet("Спеціфікація")
        rows = sheet.get_all_values()
        # Колонки: Артикул боксу | Назва боксу | Артикул сировини | Назва сировини | Норма на 1 бокс
        recipes = {}
        if len(rows) > 1:
            for r in rows[1:]:
                if len(r) >= 5:
                    b_art, b_name, c_art, c_name, qty = r[0], r[1], r[2], r[3], r[4]
                    if not b_art: continue
                    if b_art not in recipes:
                        recipes[b_art] = {"article": b_art, "name": b_name, "components": []}
                    
                    try:
                        parsed_qty = float(qty.replace(',', '.'))
                    except:
                        parsed_qty = 1.0

                    recipes[b_art]["components"].append({
                        "article": c_art,
                        "name": c_name,
                        "qty": parsed_qty
                    })
        return recipes
    except Exception as e:
        print("Помилка завантаження специфікацій:", e)
        return {}
