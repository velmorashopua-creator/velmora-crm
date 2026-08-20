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

# Единая панель навигации по всем разделам CRM
def get_nav_html(active_tab="home"):
    tabs = [
        ("home", "📦 Головна", "/"),
        ("clients", "👥 Клієнти", "/clients"),
        ("orders", "📋 Замовлення", "/orders"),
        ("accounting", "💰 Улік", "/accounting"),
        ("novaposhta", "🚚 Нова Пошта", "/novaposhta")
    ]
    
    links_html = ""
    for tab_id, label, url in tabs:
        style = "padding: 10px 18px; border-radius: 8px; text-decoration: none; font-weight: bold; border: 1px solid #D9CEBF; font-size: 0.9rem;"
        if active_tab == tab_id:
            style += " background: #8C7262; color: white;"
        else:
            style += " background: #FFF; color: #4A4039;"
        links_html += f"<a href='{url}' style='{style}'>{label}</a>"

    return f"<div style='display: flex; gap: 10px; margin-bottom: 25px; flex-wrap: wrap;'>{links_html}</div>"

# Общий базовый стиль для страниц
def base_layout(title, content, active_tab):
    return f"""
    <!DOCTYPE html>
    <html lang="uk">
    <head>
        <meta charset="UTF-8">
        <title>Velmora CRM | {title}</title>
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
            body {{ background-color: #FAF8F5; color: #4A4039; padding: 30px; }}
            .container {{ max-width: 1300px; margin: 0 auto; }}
            h1 {{ font-size: 1.8rem; color: #4A4039; margin-bottom: 5px; }}
            .card {{ background: #FFF; border-radius: 12px; border: 1px solid #EFECE6; box-shadow: 0 4px 15px rgba(0,0,0,0.02); padding: 20px; margin-top: 20px; }}
            .table-container {{ background: #FFF; border-radius: 12px; border: 1px solid #EFECE6; box-shadow: 0 4px 15px rgba(0,0,0,0.02); overflow-x: auto; padding: 10px; margin-top: 20px; }}
            table {{ width: 100%; border-collapse: collapse; text-align: left; }}
            th {{ background: #F3EFEA; padding: 14px 15px; font-size: 0.9rem; color: #5C4033; border-bottom: 2px solid #E8DCC4; }}
            td {{ padding: 12px 15px; border-bottom: 1px solid #EFECE6; font-size: 0.95rem; }}
        </style>
    </head>
    <body>
        <div class="container">
            {get_nav_html(active_tab)}
            {content}
        </div>
    </body>
    </html>
    """

# --- 1. ГОЛОВНА ---
@app.get("/", response_class=HTMLResponse)
def read_root():
    try:
        sheet = get_google_sheet()
        rows = sheet.get_all_values()
    except:
        rows = []

    total_orders = len(rows) - 1 if len(rows) > 1 else 0
    content = f"""
    <h1>📦 Головна панель</h1>
    <p style="color: #8C7B70; margin-bottom: 20px;">Оперативна звітність та стан бізнесу</p>
    <div style="display: flex; gap: 20px;">
        <div class="card" style="flex: 1;">
            <div style="color: #8C7B70; font-size: 0.9rem;">Всього замовлень</div>
            <div style="font-size: 2rem; font-weight: bold; margin-top: 5px;">{total_orders}</div>
        </div>
        <div class="card" style="flex: 1;">
            <div style="color: #8C7B70; font-size: 0.9rem;">Статус системи</div>
            <div style="font-size: 1.2rem; font-weight: bold; color: #28A745; margin-top: 10px;">🟢 Онлайн (Render)</div>
        </div>
    </div>
    """
    return base_layout("Головна", content, "home")

# --- 2. КЛІЄНТИ ---
@app.get("/clients", response_class=HTMLResponse)
def get_clients_page():
    try:
        sheet = get_google_sheet()
        rows = sheet.get_all_values()[1:]
    except:
        rows = []

    clients_html = ""
    if rows:
        for r in rows:
            if len(r) >= 6:
                clients_html += f"<tr><td><b>{r[1]}</b></td><td>{r[2]}</td><td>{r[3]}</td><td>{r[4]}</td></tr>"
    else:
        clients_html = "<tr><td colspan='4' style='text-align: center; color: #8C7B70;'>Поки що немає клієнтів</td></tr>"

    content = f"""
    <h1>👥 База клієнтів</h1>
    <p style="color: #8C7B70; margin-bottom: 20px;">Список усіх покупців</p>
    <div class="table-container">
        <table>
            <thead><tr><th>Ім'я</th><th>Телефон</th><th>Улюбленець</th><th>Місто</th></tr></thead>
            <tbody>{clients_html}</tbody>
        </table>
    </div>
    """
    return base_layout("Клієнти", content, "clients")

# --- 3. ЗАМОВЛЕННЯ ---
@app.get("/orders", response_class=HTMLResponse)
def get_orders_page():
    try:
        sheet = get_google_sheet()
        rows = sheet.get_all_values()[1:]
    except:
        rows = []

    orders_html = ""
    if rows:
        for r in reversed(rows):
            orders_html += f"<tr><td>{r[0]}</td><td><b>{r[1]}</b></td><td>{r[2]}</td><td>{r[6]}</td><td><span style='background: #E8DCC4; padding: 4px 8px; border-radius: 8px;'>{r[7]}</span></td></tr>"
    else:
        orders_html = "<tr><td colspan='5' style='text-align: center; color: #8C7B70;'>Немає замовлень</td></tr>"

    content = f"""
    <h1>📋 Усі замовлення</h1>
    <p style="color: #8C7B70; margin-bottom: 20px;">Керування статусами та деталями</p>
    <div class="table-container">
        <table>
            <thead><tr><th>Дата</th><th>Ім'я</th><th>Телефон</th><th>Товар</th><th>Статус</th></tr></thead>
            <tbody>{orders_html}</tbody>
        </table>
    </div>
    """
    return base_layout("Замовлення", content, "orders")

# --- 4. УЛІК ---
@app.get("/accounting", response_class=HTMLResponse)
def get_accounting_page():
    content = """
    <h1>💰 Улік та Фінанси</h1>
    <p style="color: #8C7B70; margin-bottom: 20px;">Контроль доходів, витрат та залишків товарів</p>
    <div class="card">
        <h3>📊 Розділ в розробці</h3>
        <p style="color: #8C7B70; margin-top: 10px;">Здесь будет финансовая аналитика, подсчет выручки и складской учет боксов.</p>
    </div>
    """
    return base_layout("Улік", content, "accounting")

# --- 5. НОВА ПОШТА ---
@app.get("/novaposhta", response_class=HTMLResponse)
def get_novaposhta_page():
    content = """
    <h1>🚚 Нова Пошта</h1>
    <p style="color: #8C7B70; margin-bottom: 20px;">Створення ЕН та відстеження посилок</p>
    <div class="card">
        <h3>📦 Інтеграція з API Нової Пошти</h3>
        <p style="color: #8C7B70; margin-top: 10px;">Здесь будет генерация экспресс-накладных в один клик.</p>
    </div>
    """
    return base_layout("Нова Пошта", content, "novaposhta")

@app.post("/add-order")
def add_order(order: Order):
    order_data = order.dict()
    order_data["date"] = datetime.now().strftime("%d.%m.%Y %H:%M")
    order_data["status"] = "Новий"
    save_order_to_sheet(order_data)
    return {"status": "success", "message": "Замовлення прийнято"}
