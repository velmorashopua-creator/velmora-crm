from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List
from database import save_order_to_sheet, get_google_sheet, update_order_in_sheet, add_prichid_bulk, add_vydatky
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- МОДЕЛИ ДАННЫХ ---
class Order(BaseModel):
    name: str; phone: str; pet: str; city: str; warehouse: str; product: str

class OrderUpdate(BaseModel):
    row_id: int; status: str; ttn: str

class VydatkyData(BaseModel):
    category: str; sum: float; comment: str; order_id: str

# Модели для Приходной накладной (Массовая загрузка)
class PrichidItem(BaseModel):
    article: str
    name: str
    qty: int
    total_sum: float

class BulkPrichid(BaseModel):
    doc_number: str
    supplier: str
    items: List[PrichidItem]

# --- ВИЗУАЛ (МЕНЮ И ШАБЛОН) ---
def get_sidebar_html(active_tab="home"):
    tabs = [
        ("home", "📦 Головна", "/"),
        ("clients", "👥 Клієнти", "/clients"),
        ("orders", "📋 Замовлення", "/orders"),
        ("accounting", "💰 Облік та Склад", "/accounting"),
        ("novaposhta", "🚚 Нова Пошта", "/novaposhta"),
        ("messages", "💬 Повідомлення", "/messages")
    ]
    links_html = ""
    for tab_id, label, url in tabs:
        is_active = (active_tab == tab_id)
        bg = "#8C7262" if is_active else "transparent"
        col = "#FFF" if is_active else "#4A4039"
        fw = "bold" if is_active else "600"
        links_html += f"<a href='{url}' style='display: block; padding: 12px 16px; border-radius: 8px; text-decoration: none; font-weight: {fw}; font-size: 0.95rem; background: {bg}; color: {col}; margin-bottom: 8px; transition: 0.2s;'>{label}</a>"
    return f"<div style='width: 260px; background: #FFF; padding: 25px 20px; border-radius: 12px; border: 1px solid #EFECE6; box-shadow: 0 4px 15px rgba(0,0,0,0.02); height: fit-content; flex-shrink: 0;'><div style='font-weight: bold; color: #5C4033; font-size: 1.2rem; margin-bottom: 25px; padding-left: 5px;'>Velmora CRM</div>{links_html}</div>"

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
            h1 {{ font-size: 1.8rem; color: #4A4039; margin-bottom: 15px; }}
            .card {{ background: #FFF; border-radius: 12px; border: 1px solid #EFECE6; box-shadow: 0 4px 15px rgba(0,0,0,0.02); padding: 25px; margin-top: 20px; }}
            table {{ width: 100%; border-collapse: collapse; text-align: left; }}
            th {{ background: #F3EFEA; padding: 12px; font-size: 0.9rem; color: #5C4033; border-bottom: 2px solid #E8DCC4; }}
            td {{ padding: 10px; border-bottom: 1px solid #EFECE6; }}
            .form-control {{ width: 100%; padding: 8px; border: 1px solid #D9CEBF; border-radius: 6px; background: #FAF8F5; }}
            .btn-submit {{ background: #8C7262; color: #FFF; border: none; padding: 10px 20px; border-radius: 8px; font-weight: bold; cursor: pointer; }}
            .btn-submit:hover {{ background: #6E574B; }}
            .tab-btn {{ padding: 10px 20px; border: none; background: #EFECE6; cursor: pointer; font-weight: bold; border-radius: 8px 8px 0 0; margin-right: 5px; color: #8C7B70; }}
            .tab-btn.active {{ background: #FFF; color: #5C4033; border-top: 3px solid #8C7262; }}
            .tab-content {{ display: none; background: #FFF; padding: 25px; border-radius: 0 12px 12px 12px; border: 1px solid #EFECE6; }}
            .tab-content.active {{ display: block; }}
        </style>
    </head>
    <body>
        <div class="app-container">{get_sidebar_html(active_tab)}<div class="main-content">{content}</div></div>
        {extra_scripts}
    </body>
    </html>
    """

# --- МАРШРУТЫ (СТРАНИЦЫ) ---
@app.get("/", response_class=HTMLResponse)
def read_root():
    return base_layout("Головна", "<h1>📦 Головна панель</h1><div class='card'>Система працює.</div>", "home")

@app.get("/clients", response_class=HTMLResponse)
def get_clients_page():
    return base_layout("Клієнти", "<h1>👥 База клієнтів</h1><div class='card'>В розробці</div>", "clients")

@app.get("/accounting", response_class=HTMLResponse)
def get_accounting_page():
    content = """
    <h1>💰 Облік та Склад</h1>
    
    <div>
        <button class="tab-btn active" onclick="openTab(event, 'tab-prichid')">📥 Прибуткова накладна</button>
        <button class="tab-btn" onclick="openTab(event, 'tab-assembly')">🛠️ Комплектація (Збірка)</button>
        <button class="tab-btn" onclick="openTab(event, 'tab-vydatky')">💸 Операційні витрати</button>
    </div>

    <!-- ТАБ 1: ПРИХОДНАЯ НАКЛАДНАЯ -->
    <div id="tab-prichid" class="tab-content active">
        <h3 style="margin-bottom: 15px; color: #5C4033;">Створення Прибуткової Накладної</h3>
        <div style="display: flex; gap: 15px; margin-bottom: 20px;">
            <div style="flex:1;"><label>№ Накладної</label><input type="text" id="pn_doc" class="form-control" required placeholder="ПН-001"></div>
            <div style="flex:2;"><label>Постачальник</label><input type="text" id="pn_supplier" class="form-control" required placeholder="ФОП Іванов"></div>
        </div>
        
        <table id="pn-table" style="margin-bottom: 15px;">
            <thead><tr><th>Артикул</th><th>Товар / Сировина</th><th>К-сть</th><th>Загальна сума (грн)</th><th>Дія</th></tr></thead>
            <tbody id="pn-body">
                <tr>
                    <td><input type="text" class="i-art form-control" placeholder="Напр. BOX-01"></td>
                    <td><input type="text" class="i-name form-control" placeholder="Коробка крафтова"></td>
                    <td><input type="number" class="i-qty form-control" value="1"></td>
                    <td><input type="number" step="0.01" class="i-sum form-control" placeholder="0.00"></td>
                    <td><button onclick="this.closest('tr').remove()" style="padding: 5px; cursor: pointer;">❌</button></td>
                </tr>
            </tbody>
        </table>
        
        <div style="display: flex; justify-content: space-between;">
            <button onclick="addPnRow()" style="padding: 8px 15px; border: 1px dashed #8C7262; background: transparent; cursor: pointer; border-radius: 6px; font-weight: bold; color: #8C7262;">+ Додати рядок</button>
            <button onclick="submitPn()" class="btn-submit">💾 Провести накладну</button>
        </div>
    </div>

    <!-- ТАБ 2: КОМПЛЕКТАЦИЯ (СБОРКА БОКСОВ) -->
    <div id="tab-assembly" class="tab-content">
        <h3 style="margin-bottom: 15px; color: #5C4033;">Акт комплектації боксу</h3>
        <p style="color: #8C7B70; font-size: 0.9rem; margin-bottom: 15px;">Система спише сировину зі складу і створить готовий бокс.</p>
        <div class="card" style="margin-top: 0; background: #FAF8F5;">В розробці: тут буде форма для вибору сировини (іграшки, стрейч, коробки) та перетворення їх на один готовий продукт.</div>
    </div>

    <!-- ТАБ 3: ОПЕРАЦИОННЫЕ РАСХОДЫ -->
    <div id="tab-vydatky" class="tab-content">
        <h3 style="margin-bottom: 15px; color: #5C4033;">Фіксація витрат</h3>
        <form id="form-vydatky">
            <label>Категорія</label>
            <select id="v_cat" class="form-control" style="margin-bottom: 10px;">
                <option>Логістика (НП)</option><option>Реклама</option><option>Оренда/Сервіси</option><option>Канцтовари</option>
            </select>
            <label>Сума (грн)</label>
            <input type="number" step="0.01" id="v_sum" class="form-control" style="margin-bottom: 10px;" required>
            <label>Коментар</label>
            <input type="text" id="v_com" class="form-control" style="margin-bottom: 10px;">
            <button type="submit" class="btn-submit" style="background: #A35D5D;">Зафіксувати</button>
        </form>
    </div>
    """
    
    scripts = """
    <script>
        // Перемикання табів
        function openTab(evt, tabName) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            document.getElementById(tabName).classList.add('active');
            evt.currentTarget.classList.add('active');
        }

        // Динамічне додавання рядків в накладну
        function addPnRow() {
            const tbody = document.getElementById('pn-body');
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><input type="text" class="i-art form-control"></td>
                <td><input type="text" class="i-name form-control"></td>
                <td><input type="number" class="i-qty form-control" value="1"></td>
                <td><input type="number" step="0.01" class="i-sum form-control"></td>
                <td><button onclick="this.closest('tr').remove()" style="padding: 5px; cursor: pointer;">❌</button></td>
            `;
            tbody.appendChild(tr);
        }

        // Відправка Прибуткової Накладної на сервер
        async function submitPn() {
            const docNum = document.getElementById('pn_doc').value;
            const supplier = document.getElementById('pn_supplier').value;
            if(!docNum || !supplier) return alert("Заповніть номер накладної та постачальника!");

            const rows = document.querySelectorAll('#pn-body tr');
            const items = [];
            
            rows.forEach(row => {
                const art = row.querySelector('.i-art').value;
                const name = row.querySelector('.i-name').value;
                const qty = row.querySelector('.i-qty').value;
                const sum = row.querySelector('.i-sum').value;
                if(art && name && qty && sum) {
                    items.push({ article: art, name: name, qty: parseInt(qty), total_sum: parseFloat(sum) });
                }
            });

            if(items.length === 0) return alert("Додайте хоча б один товар!");

            try {
                const response = await fetch('/add-prichid-bulk', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ doc_number: docNum, supplier: supplier, items: items })
                });
                if(response.ok) {
                    alert('Накладну успішно проведено!');
                    document.getElementById('pn-body').innerHTML = '';
                    addPnRow(); // Повертаємо пустий рядок
                }
            } catch (err) { alert('Помилка зєднання.'); }
        }

        // Обробка форми Видатків
        document.getElementById('form-vydatky').addEventListener('submit', async (e) => {
            e.preventDefault();
            const data = {
                category: document.getElementById('v_cat').value,
                sum: parseFloat(document.getElementById('v_sum').value),
                comment: document.getElementById('v_com').value,
                order_id: ""
            };
            try {
                const response = await fetch('/add-vydatky', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
                if(response.ok) { alert('Витрату зафіксовано!'); e.target.reset(); }
            } catch (err) {}
        });
    </script>
    """
    return base_layout("Облік", content, "accounting", extra_scripts=scripts)

@app.get("/orders", response_class=HTMLResponse)
def get_orders_page():
    return base_layout("Замовлення", "<h1>📋 Усі замовлення</h1><div class='card'>В розробці</div>", "orders")

@app.get("/novaposhta", response_class=HTMLResponse)
def get_novaposhta_page():
    return base_layout("Нова Пошта", "<h1>🚚 Нова Пошта</h1><div class='card'>В розробці</div>", "novaposhta")

@app.get("/messages", response_class=HTMLResponse)
def get_messages_page():
    return base_layout("Повідомлення", "<h1>💬 Повідомлення</h1><div class='card'>В розробці</div>", "messages")

# --- API РОУТЫ ---
@app.post("/add-prichid-bulk")
def add_prichid_bulk_route(data: BulkPrichid):
    date_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    rows_to_insert = []
    
    # Формируем строки точно под колонки вашего скриншота:
    # Дата | № Прибуткової | Артикул | Товар | Кількість | сума | постачальник | собівартість
    for item in data.items:
        unit_cost = round(item.total_sum / item.qty, 2) if item.qty > 0 else 0
        row = [
            date_str,
            data.doc_number,
            item.article,
            item.name,
            str(item.qty),
            str(item.total_sum),
            data.supplier,
            str(unit_cost)
        ]
        rows_to_insert.append(row)
        
    add_prichid_bulk(rows_to_insert)
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
