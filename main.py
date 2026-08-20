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

@app.get("/", response_class=HTMLResponse)
def read_root():
    try:
        sheet = get_google_sheet()
        rows = sheet.get_all_values()
    except Exception as e:
        rows = []

    # Считаем статистику для карточек
    total_orders = len(rows) - 1 if len(rows) > 1 else 0
    new_orders_count = 0
    
    table_rows_html = ""
    if len(rows) > 1:
        header = rows[0]
        data_rows = rows[1:]
        
        # Считаем новые заявки
        for r in data_rows:
            if len(r) > 7 and r[7].lower() in ["новий", "новый"]:
                new_orders_count += 1

        # Формируем строки таблицы с красивыми бейджами статусов
        for row in reversed(data_rows): # Свежие сверху
            table_rows_html += "<tr>"
            for idx, cell in enumerate(row):
                # Если это колонка со статусом (обычно последняя)
                if idx == 7:
                    badge_bg = "#E8DCC4" if cell.lower() in ["новий", "новый"] else "#D4EDDA"
                    cell_content = f"<span style='background: {badge_bg}; padding: 4px 10px; border-radius: 12px; font-size: 0.85rem; font-weight: bold;'>{cell}</span>"
                else:
                    cell_content = cell
                table_rows_html += f"<td style='padding: 12px 15px; border-bottom: 1px solid #EFECE6; font-size: 0.95rem;'>{cell_content}</td>"
            table_rows_html += "</tr>"
    else:
        table_rows_html = "<tr><td colspan='8' style='text-align: center; padding: 20px; color: #8C7B70;'>Поки що немає замовлень</td></tr>"

    html_content = f"""
    <!DOCTYPE html>
    <html lang="uk">
    <head>
        <meta charset="UTF-8">
        <title>Velmora CRM | Головна</title>
        <meta http-equiv="refresh" content="30">
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
            body {{ background-color: #FAF8F5; color: #4A4039; padding: 30px; }}
            .container {{ max-width: 1300px; margin: 0 auto; }}
            .header-flex {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }}
            h1 {{ font-size: 1.8rem; color: #4A4039; }}
            .stats-grid {{ display: flex; gap: 20px; margin-bottom: 30px; }}
            .stat-card {{ background: #FFF; padding: 20px 25px; border-radius: 12px; border: 1px solid #EFECE6; flex: 1; box-shadow: 0 4px 15px rgba(0,0,0,0.02); }}
            .stat-title {{ font-size: 0.9rem; color: #8C7B70; margin-bottom: 5px; }}
            .stat-value {{ font-size: 1.8rem; font-weight: bold; color: #4A4039; }}
            .table-container {{ background: #FFF; border-radius: 12px; border: 1px solid #EFECE6; box-shadow: 0 4px 15px rgba(0,0,0,0.02); overflow-x: auto; padding: 10px; }}
            table {{ width: 100%; border-collapse: collapse; text-align: left; }}
            th {{ background: #F3EFEA; padding: 14px 15px; font-size: 0.9rem; color: #5C4033; border-bottom: 2px solid #E8DCC4; }}
            .refresh-btn {{ background: #8C7262; color: #FFF; border: none; padding: 10px 20px; border-radius: 8px; font-weight: bold; cursor: pointer; text-decoration: none; display: inline-block; }}
            .refresh-btn:hover {{ background: #6E574B; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header-flex">
                <div>
                    <h1>📦 Velmora CRM</h1>
                    <p style="color: #8C7B70; font-size: 0.95rem;">Панель управління та облік замовлень</p>
                </div>
                <a href="https://velmora-crm.onrender.com/" class="refresh-btn">🔄 Оновити</a>
            </div>

            <!-- Блок метрик (Дашборд) -->
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-title">Всього замовлень</div>
                    <div class="stat-value">{total_orders}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">🔥 Нові заявки</div>
                    <div class="stat-value" style="color: #D9534F;">{new_orders_count}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">🚚 В роботі / Відправлено</div>
                    <div class="stat-value">0</div>
                </div>
            </div>

            <!-- Таблиця замовлень -->
            <div class="table-container">
                <h3 style="padding: 15px 15px 5px 15px; color: #4A4039; font-size: 1.2rem;">Останні надходження</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Дата</th>
                            <th>Ім'я</th>
                            <th>Телефон</th>
                            <th>Улюбленець</th>
                            <th>Місто</th>
                            <th>Відділення НП</th>
                            <th>Товар</th>
                            <th>Статус</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows_html}
                    </tbody>
                </table>
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
