import os
import json
import gspread
from google.oauth2.service_account import Credentials
from config import SPREADSHEET_NAME

def get_google_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # Берем ключ из защищенной переменной окружения Render
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    creds_dict = json.loads(creds_json)
    
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(credentials)
    return client.open(SPREADSHEET_NAME).worksheet("Замовлення")

def save_order_to_sheet(order_data: dict):
    sheet = get_google_sheet()
    
    row = [
        order_data.get("date", ""),
        order_data.get("name", ""),
        order_data.get("phone", ""),
        order_data.get("pet", ""),
        order_data.get("city", ""),
        order_data.get("warehouse", ""),
        order_data.get("product", ""),
        order_data.get("status", "Новий")
    ]
    
    sheet.append_row(row)
