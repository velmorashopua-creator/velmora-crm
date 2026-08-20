from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from database import save_order_to_sheet, get_google_sheet, update_order_in_sheet, add_prichid, add_vydatky
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- МОДЕЛІ ДАНИХ ---
class Order(BaseModel):
    name: str
    phone: str
    pet: str
    city: str
    warehouse: str
    product: str

class OrderUpdate(BaseModel):
    row_id: int
    status: str
    ttn: str

class PrichidData(BaseModel):
    article: str
    name: str
    qty: int
    total_sum: float
    supplier: str

class VydatkyData(BaseModel):
    category: str
    sum: float
    comment: str
    order_id: str

# --- ВІЗУАЛ (МЕНЮ ТА ШАБЛОН) ---
def get_sidebar_html(active_tab="home"):
    tabs = [
        ("home", "📦 Головна", "/"),
        ("clients", "👥 Клієнти", "/clients"),
        ("orders", "📋 Замовлення", "/orders"),
        ("accounting", "💰 Облік", "/accounting"),
        ("novaposhta", "🚚 Нова Пошта", "/novaposhta"),
        ("messages", "💬 Повідомлення", "/messages")
    ]
    
    links_html = ""
    for tab_id, label, url in tabs:
        is_active = (active_tab == tab_id)
        bg_color = "#8C7262" if is_active else "transparent"
        text_color = "#FFF" if is_active else "#4A4039"
        border_color = "#8C7262" if is_active else "transparent"
        font_weight = "bold" if is_active else "600"
        
        links_html += f"""
        <a href='{url}' style='
            display: block; padding: 12px 16px; border-radius: 8px; text-decoration: none; 
            font-weight: {font_weight}; font-size: 0.95rem; background: {bg_color}; 
            color: {text_color}; border: 1px solid {border_color}; margin-bottom: 8px; transition: all 0.2s;
        '>{label}</a>
        """

    return f"""
    <div style='width: 260px; background: #FFF; padding: 25px 20px; border-radius: 12px; border: 1px solid #EFECE6; box-shadow: 0 4px 15px rgba(0,0,0,0.02); height: fit-content; flex-shrink: 0;'>
        <div style='font-weight: bold; color: #5C4033; font-size: 1.2rem; margin-bottom: 25px; padding-left: 5px;'>Velmora CRM</div>
        {links_html}
    </div>
    """

def base_layout(title, content, active_tab, extra_scripts=""):
    return f"""
    <!DOCTYPE html>
    <html lang="uk">
    <head>
        <meta charset="UTF-8">
        <title>Velmora CRM | {title}</title>
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
            body {{ background-color: #FAF8F5; color: #4A4039; padding: 30px; }}
            .app-container {{ max-width: 1400px; margin: 0 auto; display: flex; gap: 30px; align-items: flex-start; }}
            .main-content {{ flex: 1; min-width: 0; }}
            h1 {{ font-size: 1.8rem; color: #4A4039; margin-bottom: 5px; }}
            .card {{ background: #FFF; border-radius: 12px; border: 1px solid #EFECE6; box-shadow: 0 4px 15px rgba(0,0,0,0.02); padding: 25px; margin-top: 20px; }}
            .table-container {{ background: #FFF; border-radius: 12px; border: 1px solid #EFECE6; box-shadow: 0 4px 15px rgba(0,0,0,0.02); overflow-x: auto; padding: 10px; margin-top: 20px; }}
            table {{ width: 100%; border-collapse: collapse; text-align: left; }}
            th {{ background: #F3EFEA; padding: 14px 15px; font-size: 0.9rem; color: #5C4033; border-bottom: 2px solid #E8DCC4; }}
            td {{ padding: 12px 15px; border-bottom: 1px solid #EFECE6; font-size: 0.95rem; }}
            .action-btn {{ background: #E8DCC4; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-weight: bold; }}
            .action-btn:hover {{ background: #D9CEBF; }}
            
            /* Стилі для форм */
            .form-group {{ margin-bottom: 15px; }}
            .form-group label {{ display: block; margin-bottom: 5px; font-size: 0.9rem; color: #8C7B70; }}
            .form-control {{ width: 100%; padding: 10px; border: 1px solid #D9CEBF; border-radius: 6px; background: #FAF8F5; font-size: 1rem; color: #4A4039; }}
            .btn-submit {{ background: #8C7262; color: #FFF; border: none; padding: 10px 20px; border-radius: 8px; font-weight: bold; cursor: pointer; width: 100%; font-size: 1rem; }}
            .btn-submit:hover {{ background: #6E574B; }}
        </style>
    </head>
    <body>
        <div class="app-container">
            {get_sidebar_html(active_tab)}
            <div class="main-content">
                {content}
            </div>
        </div>
        {extra_scripts}
    </body>
    </html>
    """

# --- СТОРІНКИ ---

@app.get("/", response_class=HTMLResponse)
def read_root():
    try:
        sheet = get_google_sheet()
        rows = sheet.get_all_values()
    except:
        rows = []
    total_orders = len(rows) - 1 if len(rows) > 1 else 0
    content = f"""
    <h1>📦 Головна панель</h1><p style="color: #8C7B70; margin-bottom: 20px;">Оперативна звітність</p>
    <div style="display: flex; gap: 20px; flex-wrap: wrap;">
        <div class="card" style="flex: 1; min-width: 220px; margin-top: 0;"><div style="color: #8C7B70; font-size: 0.9rem;">Всього замовлень</div><div style="font-size: 2.2rem; font-weight: bold; margin-top: 5px; color: #4A4039;">{total_orders}</div></div>
    </div>
    """
    return base_layout("Головна", content, "home")

@app.get("/clients", response_class=HTMLResponse)
def get_clients_page():
    return base_layout("Клієнти", "<h1>👥 База клієнтів</h1><div class='card'>В розробці</div>", "clients")

@app.get("/orders", response_class=HTMLResponse)
def get_orders_page():
    try:
        sheet = get_google_sheet("Замовлення")
        rows = sheet.get_all_values()[1:]
    except:
        rows = []

    orders_html = ""
    status_list = ["Новий", "В роботі", "Відправлено", "Отримано", "Виконано"]
    
    if rows:
        for idx, r in enumerate(reversed(rows)):
            original_row_num = len(rows) - idx + 1
            date, name, phone = r[0], r[1], r[2]
            product = r[6] if len(r) > 6 else ""
            status = r[7] if len(r) > 7 else "Новий"
            ttn = r[8] if len(r) > 8 else ""

            options = "".join([f"<option value='{s}' {'selected' if s == status else ''}>{s}</option>" for s in status_list])
            
            orders_html += f"""
            <tr>
                <td>{date}</td>
                <td><b>{name}</b><br><span style='font-size:0.8rem; color:#8C7B70;'>{phone}</span></td>
                <td>{product}</td>
                <td>
                    <select class='status-select' style='padding: 6px; border-radius: 6px; border: 1px solid #D9CEBF; background: #FAF8F5;'>
                        {options}
                    </select>
                </td>
                <td>
                    <input type='text' class='ttn-input' value='{ttn}' placeholder='Номер ТТН' style='padding: 6px; border-radius: 6px; border: 1px solid #D9CEBF; width: 130px; background: #FAF8F5;'>
                </td>
                <td>
                    <button class='action-btn' onclick='updateOrder(this, {original_row_num})'>💾</button>
                </td>
            </tr>
            """
    else:
        orders_html = "<tr><td colspan='6' style='text-align: center; color: #8C7B70;'>Немає замовлень</td></tr>"

    content = f"""
    <h1>📋 Усі замовлення</h1>
    <p style="color: #8C7B70; margin-bottom: 20px;">Керування статусами та ТТН</p>
    <div class="table-container">
        <table>
            <thead><tr><th>Дата</th><th>Клієнт</th><th>Товар</th><th>Статус</th><th>ТТН</th><th>Дія</th></tr></thead>
            <tbody>{orders_html}</tbody>
        </table>
    </div>
    """
    
    scripts = """
    <script>
    async function updateOrder(btn, rowNum) {
        const tr = btn.closest('tr');
        const status = tr.querySelector('.status-select').value;
        const ttn = tr.querySelector('.ttn-input').value;
        
        btn.innerText = '⏳';
        
        try {
            const response = await fetch('/update-order', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({row_id: rowNum, status: status, ttn: ttn})
            });
            if (response.ok) {
                btn.innerText = '✅';
                setTimeout(() => btn.innerText = '💾', 2000);
            } else {
                btn.innerText = '❌';
            }
        } catch(e) {
            btn.innerText = '❌';
        }
    }
    </script>
    """
    return base_layout("Замовлення", content, "orders", extra_scripts=scripts)

@app.get("/accounting", response_class=HTMLResponse)
def get_accounting_page():
    content = """
    <h1>💰 Облік та Фінанси</h1>
    <p style="color: #8C7B70; margin-bottom: 20px;">Внесення приходу на склад та операційних витрат</p>
    
    <div style="display: flex; gap: 30px; flex-wrap: wrap;">
        <!-- Форма ПРИХІД -->
        <div class="card" style="flex: 1; min-width: 300px; margin-top: 0;">
            <h3 style="margin-bottom: 20px; color: #5C4033;">📥 Оприбуткувати товар (Прихід)</h3>
            <form id="form-prichid">
                <div class="form-group">
                    <label>Артикул</label>
                    <input type="text" id="p_article" class="form-control" required placeholder="Напр. BOX-01">
                </div>
                <div class="form-group">
                    <label>Назва товару/матеріалу</label>
                    <input type="text" id="p_name" class="form-control" required placeholder="Коробка подарункова">
                </div>
                <div style="display: flex; gap: 15px;">
                    <div class="form-group" style="flex: 1;">
                        <label>Кількість (шт)</label>
                        <input type="number" id="p_qty" class="form-control" required>
                    </div>
                    <div class="form-group" style="flex: 1;">
                        <label>Сума закупівлі (грн)</label>
                        <input type="number" step="0.01" id="p_sum" class="form-control" required>
                    </div>
                </div>
                <div class="form-group">
                    <label>Постачальник</label>
                    <input type="text" id="p_supplier" class="form-control" placeholder="ФОП Іванов / Пром">
                </div>
                <button type="submit" class="btn-submit">Внести на склад</button>
            </form>
        </div>

        <!-- Форма ВИТРАТИ -->
        <div class="card" style="flex: 1; min-width: 300px; margin-top: 0;">
            <h3 style="margin-bottom: 20px; color: #5C4033;">💸 Інші витрати (Видатки)</h3>
            <form id="form-vydatky">
                <div class="form-group">
                    <label>Категорія витрат</label>
                    <select id="v_category" class="form-control" required>
                        <option value="Логістика (НП)">Логістика (Нова Пошта)</option>
                        <option value="Реклама (FB/Insta)">Реклама (FB/Insta)</option>
                        <option value="Пакування">Пакування (скотч, плівка)</option>
                        <option value="Оренда / Сервіси">Оренда / Сервіси (Домен, Render)</option>
                        <option value="Інше">Інше</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Сума (грн)</label>
                    <input type="number" step="0.01" id="v_sum" class="form-control" required>
                </div>
                <div class="form-group">
                    <label>Коментар / Призначення</label>
                    <input type="text" id="v_comment" class="form-control" placeholder="Оплата за доставку...">
                </div>
                <div class="form-group">
                    <label>№ Замовлення (якщо стосується клієнта)</label>
                    <input type="text" id="v_order_id" class="form-control" placeholder="Необов'язково">
                </div>
                <button type="submit" class="btn-submit" style="background: #A35D5D;">Зафіксувати витрату</button>
            </form>
        </div>
    </div>
    """

    scripts = """
    <script>
        // Обробка форми Приходу
        document.getElementById('form-prichid').addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = e.target.querySelector('button');
            btn.innerText = 'Завантаження...';
            
            const data = {
                article: document.getElementById('p_article').value,
                name: document.getElementById('p_name').value,
                qty: parseInt(document.getElementById('p_qty').value),
                total_sum: parseFloat(document.getElementById('p_sum').value),
                supplier: document.getElementById('p_supplier').value
            };

            try {
                const response = await fetch('/add-prichid', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                if(response.ok) {
                    alert('Товар успішно внесено на склад!');
                    e.target.reset();
                } else {
                    alert('Помилка збереження.');
                }
            } catch (err) {
                alert('Помилка з\'єднання.');
            } finally {
                btn.innerText = 'Внести на склад';
            }
        });

        // Обробка форми Видатків
        document.getElementById('form-vydatky').addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = e.target.querySelector('button');
            btn.innerText = 'Завантаження...';
            
            const data = {
                category: document.getElementById('v_category').value,
                sum: parseFloat(document.getElementById('v_sum').value),
                comment: document.getElementById('v_comment').value,
                order_id: document.getElementById('v_order_id').value
            };

            try {
                const response = await fetch('/add-vydatky', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                if(response.ok) {
                    alert('Витрату успішно зафіксовано!');
                    e.target.reset();
                } else {
                    alert('Помилка збереження.');
                }
            } catch (err) {
                alert('Помилка з\'єднання.');
            } finally {
                btn.innerText = 'Зафіксувати витрату';
            }
        });
    </script>
    """
    return base_layout("Облік", content, "accounting", extra_scripts=scripts)

@app.get("/novaposhta", response_class=HTMLResponse)
def get_novaposhta_page():
    return base_layout("Нова Пошта", "<h1>🚚 Нова Пошта</h1><div class='card'>В розробці</div>", "novaposhta")

@app.get("/messages", response_class=HTMLResponse)
def get_messages_page():
    return base_layout("Повідомлення", "<h1>💬 Повідомлення</h1><div class='card'>В розробці</div>", "messages")

# --- АПІ РОУТИ ДЛЯ ЗАПИСУ ДАНИХ ---

@app.post("/add-order")
def add_order(order: Order):
    order_data = order.dict()
    order_data["date"] = datetime.now().strftime("%d.%m.%Y %H:%M")
    order_data["status"] = "Новий"
    save_order_to_sheet(order_data)
    return {"status": "success", "message": "Замовлення прийнято"}

@app.post("/update-order")
def update_order_route(data: OrderUpdate):
    update_order_in_sheet(data.row_id, data.status, data.ttn)
    return {"status": "success"}

@app.post("/add-prichid")
def add_prichid_route(data: PrichidData):
    # Рахуємо собівартість одиниці
    unit_cost = round(data.total_sum / data.qty, 2) if data.qty > 0 else 0
    row_data = {
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "article": data.article,
        "name": data.name,
        "qty": str(data.qty),
        "total_sum": str(data.total_sum),
        "supplier": data.supplier,
        "unit_cost": str(unit_cost)
    }
    add_prichid(row_data)
    return {"status": "success"}

@app.post("/add-vydatky")
def add_vydatky_route(data: VydatkyData):
    row_data = {
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "category": data.category,
        "sum": str(data.sum),
        "comment": data.comment,
        "order_id": data.order_id
    }
    add_vydatky(row_data)
    return {"status": "success"}
