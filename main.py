from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from database import save_order_to_sheet, get_google_sheet
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Order(BaseModel):
    name: str
    phone: str
    pet: str
    city: str
    warehouse: str
    product: str

# ГЛАВНАЯ СТРАНИЦА (CRM Интерфейс)
@app.get("/", response_class=HTMLResponse)
def read_root():
    try:
        sheet = get_google_sheet()
        rows = sheet.get_all_values() # Получаем все строки из таблицы
    except Exception as e:
        rows = [["Ошибка загрузки данных", str(e)]]

    # Строим простую и красивую HTML-таблицу для главной страницы
    table_html = "<table border='1' style='border-collapse: collapse; width: 100%; font-family: sans-serif; padding: 8px;'>"
    for i, row in enumerate(rows):
        tag = "th" if i == 0 else "td"
        table_html += "<tr>"
        for cell in row:
            table_html += f"<{tag} style='padding: 10px; text-align: left;'>{cell}</{tag}>"
        table_html += "</tr>"
    table_html += "</table>"

    html_content = f"""
    <!DOCTYPE html>
    <html lang="uk">
    <head>
        <meta charset="UTF-8">
        <title>Velmora CRM | Головна</title>
        <meta http-equiv="refresh" content="30"> <!-- Автообновление каждые 30 сек -->
    </head>
    <body style="font-family: sans-serif; background: #FAF8F5; color: #4A4039; padding: 20px;">
        <div style="max-width: 1200px; margin: 0 auto;">
            <h1>📦 Velmora CRM | Головна сторінка замовлень</h1>
            <p>Дані оновлюються автоматично з Google Таблиці.</p>
            <hr style="margin: 20px 0;">
            <div style="overflow-x: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
                {table_html}
            </div>
        </div>
    </body>
    </html>
    """
    return html_content

@app.post("/add-order")
def add_order(order: Order):
    order_data = order.dict()
    order_data["date"] = datetime.now().strftime("%d.%m.%Y %H:%M")
    order_data["status"] = "Новий"
    
    save_order_to_sheet(order_data)
    
    return {"status": "success", "message": "Замовлення прийнято"}
