from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List
from database import save_order_to_sheet, get_google_sheet, update_order_in_sheet, add_prichid_bulk, add_vydatky, get_specs_from_sheet, add_vitraty_bulk, add_specification_rows
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
    name: str; phone: str; pet: str; city: str; warehouse: str; product: str

class OrderUpdate(BaseModel):
    row_id: int; status: str; ttn: str

class VydatkyData(BaseModel):
    category: str; sum: float; comment: str; order_id: str

class PrichidItem(BaseModel):
    article: str
    name: str
    qty: int
    total_sum: float

class BulkPrichid(BaseModel):
    doc_number: str
    supplier: str
    items: List[PrichidItem]

class AssembleRequest(BaseModel):
    box_id: str
    qty: int

class SpecComponent(BaseModel):
    c_art: str
    c_name: str
    qty: float

class SpecificationRequest(BaseModel):
    box_art: str
    box_name: str
    components: List[SpecComponent]

# --- ЕТАПИ ВОРОНКИ ПРОДАЖІВ ---
FUNNEL_STAGES = [
    "Нове замовлення",
    "Зв'язалися",
    "Обрали бокс",
    "Очікуємо оплату",
    "Оплачено",
    "Зібрати бокс",
    "Передано на доставку",
    "Отримано",
    "Повторна покупка",
    "Підписка"
]

# --- ВІЗУАЛ (МЕНЮ ТА ШАБЛОН) ---
def get_sidebar_html(active_tab="home"):
    tabs = [
        ("home", "📦 Головна", "/"),
        ("funnel", "🎯 Воронка", "/funnel"),
        ("orders", "📋 Замовлення", "/orders"),
        ("accounting", "💰 Облік та Склад", "/accounting"),
        ("clients", "👥 Клієнти", "/clients"),
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
            body {{ background-color: #FAF8F5; color: #4A4039; padding: 30px; height: 100vh; display: flex; flex-direction: column; }}
            .app-container {{ max-width: 1600px; width: 100%; margin: 0 auto; display: flex; gap: 30px; align-items: flex-start; flex: 1; overflow: hidden; }}
            .main-content {{ flex: 1; min-width: 0; display: flex; flex-direction: column; height: 100%; overflow-y: auto; padding-right: 10px; }}
            h1 {{ font-size: 1.8rem; color: #4A4039; margin-bottom: 15px; flex-shrink: 0; }}
            .card {{ background: #FFF; border-radius: 12px; border: 1px solid #EFECE6; box-shadow: 0 4px 15px rgba(0,0,0,0.02); padding: 25px; margin-top: 20px; }}
            table {{ width: 100%; border-collapse: collapse; text-align: left; }}
            th {{ background: #F3EFEA; padding: 12px; font-size: 0.9rem; color: #5C4033; border-bottom: 2px solid #E8DCC4; }}
            td {{ padding: 6px 10px; border-bottom: 1px solid #EFECE6; }}
            .form-control {{ width: 100%; padding: 8px; border: 1px solid #D9CEBF; border-radius: 6px; background: #FFF; }}
            .btn-submit {{ background: #8C7262; color: #FFF; border: none; padding: 10px 20px; border-radius: 8px; font-weight: bold; cursor: pointer; transition: 0.2s; }}
            .btn-submit:hover {{ background: #6E574B; }}
            .btn-outline {{ padding: 8px 15px; border: 1px dashed #8C7262; background: transparent; cursor: pointer; border-radius: 6px; font-weight: bold; color: #8C7262; transition: 0.2s; }}
            .btn-outline:hover {{ background: #F3EFEA; }}
            .tab-btn {{ padding: 10px 20px; border: none; background: #EFECE6; cursor: pointer; font-weight: bold; border-radius: 8px 8px 0 0; margin-right: 5px; color: #8C7B70; }}
            .tab-btn.active {{ background: #FFF; color: #5C4033; border-top: 3px solid #8C7262; }}
            .tab-content {{ display: none; background: #FFF; padding: 25px; border-radius: 0 12px 12px 12px; border: 1px solid #EFECE6; box-shadow: 0 4px 15px rgba(0,0,0,0.02); }}
            .tab-content.active {{ display: block; }}
        </style>
    </head>
    <body>
        <div class="app-container">{get_sidebar_html(active_tab)}<div class="main-content">{content}</div></div>
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

@app.get("/funnel", response_class=HTMLResponse)
def get_funnel_page():
    try:
        sheet = get_google_sheet("Замовлення")
        rows = sheet.get_all_values()[1:]
    except:
        rows = []

    # Групуємо замовлення за статусами
    board_data = {stage: [] for stage in FUNNEL_STAGES}
    
    if rows:
        for idx, r in enumerate(rows):
            original_row_num = idx + 2
            date, name, phone = r[0], r[1], r[2]
            product = r[6] if len(r) > 6 else ""
            status = r[7] if len(r) > 7 else "Нове замовлення"
            ttn = r[8] if len(r) > 8 else ""

            # Якщо старий статус (напр. "Новий"), перекидаємо у "Нове замовлення"
            if status not in FUNNEL_STAGES:
                status = "Нове замовлення"
            
            ttn_block = f"<div class='meta' style='margin-top:5px; color:#A35D5D;'>ТТН: {ttn}</div>" if ttn else ""

            card_html = f"""
            <div class="kanban-card" id="card-{original_row_num}" draggable="true" ondragstart="drag(event, {original_row_num}, '{ttn}')">
                <h4>{name}</h4>
                <div class="meta">📞 {phone}</div>
                <div class="meta">📅 {date}</div>
                <div class="product">{product}</div>
                {ttn_block}
            </div>
            """
            board_data[status].append(card_html)

    # Генеруємо HTML колонок Канбану
    columns_html = ""
    for stage in FUNNEL_STAGES:
        cards_html = "".join(board_data[stage])
        count = len(board_data[stage])
        columns_html += f"""
        <div class="kanban-column" ondrop="drop(event, '{stage}')" ondragover="allowDrop(event)">
            <div class="kanban-header">{stage} <span style="color:#8C7B70; font-weight:normal;">({count})</span></div>
            <div class="cards-container">
                {cards_html}
            </div>
        </div>
        """

    content = f"""
    <h1>🎯 Воронка продажів</h1>
    <p style="color: #8C7B70; margin-bottom: 15px; flex-shrink: 0;">Перетягуйте картки мишкою між етапами для автоматичної зміни статусу.</p>
    <div class="kanban-board">
        {columns_html}
    </div>
    """

    scripts = """
    <style>
        .kanban-board { display: flex; gap: 15px; overflow-x: auto; padding-bottom: 15px; align-items: flex-start; flex: 1; }
        .kanban-column { background: #F3EFEA; border-radius: 8px; min-width: 270px; max-width: 270px; display: flex; flex-direction: column; border: 1px solid #D9CEBF; max-height: 100%; }
        .kanban-header { padding: 12px; font-weight: bold; color: #5C4033; text-align: center; border-bottom: 2px solid #E8DCC4; font-size: 0.95rem; background: #E8DCC4; border-radius: 8px 8px 0 0; }
        .cards-container { padding: 10px; overflow-y: auto; flex: 1; min-height: 200px; }
        .kanban-card { background: #FFF; border-radius: 6px; padding: 12px; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); cursor: grab; border: 1px solid #EFECE6; transition: 0.2s; }
        .kanban-card:active { cursor: grabbing; box-shadow: 0 4px 8px rgba(0,0,0,0.1); transform: scale(0.98); }
        .kanban-card h4 { font-size: 0.95rem; margin-bottom: 8px; color: #4A4039; }
        .kanban-card .meta { font-size: 0.8rem; color: #8C7B70; margin-bottom: 4px; }
        .kanban-card .product { font-size: 0.8rem; color: #5C4033; font-weight: 600; padding: 4px 6px; background: #FAF8F5; border-radius: 4px; display: inline-block; margin-top: 5px; border: 1px solid #EFECE6; }
    </style>
    <script>
        function allowDrop(ev) {
            ev.preventDefault();
        }

        function drag(ev, rowId, ttn) {
            ev.dataTransfer.setData("rowId", rowId);
            ev.dataTransfer.setData("ttn", ttn);
        }

        async function drop(ev, newStatus) {
            ev.preventDefault();
            var rowId = ev.dataTransfer.getData("rowId");
            var ttn = ev.dataTransfer.getData("ttn");
            
            // Знаходимо колонку, куди кинули картку
            var column = ev.target.closest('.kanban-column');
            if(!column) return;
            var container = column.querySelector('.cards-container');
            
            // Переміщуємо візуально
            var card = document.getElementById("card-" + rowId);
            container.appendChild(card);
            
            // Відправляємо запит на сервер для збереження
            try {
                const response = await fetch('/update-order', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({row_id: parseInt(rowId), status: newStatus, ttn: ttn})
                });
                
                if(response.ok) {
                    // Оновлюємо лічильники
                    setTimeout(() => window.location.reload(), 500); 
                } else {
                    alert('Помилка оновлення статусу у Google Таблиці');
                }
            } catch (e) {
                alert('Помилка зєднання');
            }
        }
    </script>
    """
    return base_layout("Воронка", content, "funnel", extra_scripts=scripts)

@app.get("/orders", response_class=HTMLResponse)
def get_orders_page():
    try:
        sheet = get_google_sheet("Замовлення")
        rows = sheet.get_all_values()[1:]
    except:
        rows = []

    orders_html = ""
    if rows:
        for idx, r in enumerate(reversed(rows)):
            original_row_num = len(rows) - idx + 1
            date, name, phone = r[0], r[1], r[2]
            product = r[6] if len(r) > 6 else ""
            status = r[7] if len(r) > 7 else "Нове замовлення"
            if status not in FUNNEL_STAGES: status = "Нове замовлення"
            ttn = r[8] if len(r) > 8 else ""

            options = "".join([f"<option value='{s}' {'selected' if s == status else ''}>{s}</option>" for s in FUNNEL_STAGES])
            
            orders_html += f"<tr><td>{date}</td><td><b>{name}</b><br><span style='font-size:0.8rem; color:#8C7B70;'>{phone}</span></td><td>{product}</td><td><select class='status-select' style='padding: 6px; border-radius: 6px; border: 1px solid #D9CEBF; background: #FAF8F5;'>{options}</select></td><td><input type='text' class='ttn-input' value='{ttn}' placeholder='Номер ТТН' style='padding: 6px; border-radius: 6px; border: 1px solid #D9CEBF; width: 130px; background: #FAF8F5;'></td><td><button class='action-btn' onclick='updateOrder(this, {original_row_num})' style='background: #E8DCC4; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer;'>💾</button></td></tr>"
    else:
        orders_html = "<tr><td colspan='6' style='text-align: center; color: #8C7B70;'>Немає замовлень</td></tr>"

    content = f"<h1>📋 Реєстр замовлень</h1><div class='table-container' style='background: #FFF; border-radius: 12px; padding: 10px;'><table><thead><tr><th>Дата</th><th>Клієнт</th><th>Товар</th><th>Статус</th><th>ТТН</th><th>Дія</th></tr></thead><tbody>{orders_html}</tbody></table></div>"
    
    scripts = "<script>async function updateOrder(btn, rowNum) { const tr = btn.closest('tr'); const status = tr.querySelector('.status-select').value; const ttn = tr.querySelector('.ttn-input').value; btn.innerText = '⏳'; try { const response = await fetch('/update-order', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({row_id: rowNum, status: status, ttn: ttn}) }); if (response.ok) { btn.innerText = '✅'; setTimeout(() => btn.innerText = '💾', 2000); } else { btn.innerText = '❌'; } } catch(e) { btn.innerText = '❌'; } } </script>"
    return base_layout("Замовлення", content, "orders", extra_scripts=scripts)

@app.get("/accounting", response_class=HTMLResponse)
def get_accounting_page():
    recipes = get_specs_from_sheet()
    box_options = "".join([f"<option value='{b_id}'>{b_data['name']} (Арт: {b_data['article']})</option>" for b_id, b_data in recipes.items()])
    if not box_options: box_options = "<option disabled>Створіть специфікацію у вкладці поруч</option>"

    pn_rows = "".join([f"<tr><td><input type='text' class='i-art form-control' list='nomenclature-list' onchange='smartFillRow(this)' placeholder='Артикул'></td><td><input type='text' class='i-name form-control' placeholder='Назва товару'></td><td><input type='number' class='i-qty form-control' placeholder='0'></td><td><input type='number' step='0.01' class='i-sum form-control' placeholder='0.00'></td><td style='text-align:center;'><button type='button' onclick='clearRow(this)' style='padding: 4px 8px; background: #FFDDDD; border: none; border-radius: 4px; cursor: pointer;'>❌</button></td></tr>" for _ in range(15)])
    spec_rows = "".join([f"<tr><td><input type='text' class='s-art form-control' list='nomenclature-list' onchange='smartFillRowSpec(this)' placeholder='Арт. сировини'></td><td><input type='text' class='s-name form-control' placeholder='Назва сировини'></td><td><input type='number' step='0.01' class='s-qty form-control' placeholder='Норма'></td></tr>" for _ in range(10)])

    content = f"""
    <h1>💰 Облік та Склад</h1>
    <datalist id="nomenclature-list"></datalist>

    <div>
        <button class="tab-btn active" onclick="openTab(event, 'tab-prichid')">📥 Прибуткова накладна</button>
        <button class="tab-btn" onclick="openTab(event, 'tab-assembly')">🛠️ Комплектація (Збірка)</button>
        <button class="tab-btn" onclick="openTab(event, 'tab-specs')">📑 Створення Специфікації</button>
        <button class="tab-btn" onclick="openTab(event, 'tab-vydatky')">💸 Видатки</button>
    </div>

    <!-- ТАБ 1: ПРИХОД -->
    <div id="tab-prichid" class="tab-content active">
        <div style="display: flex; gap: 15px; margin-bottom: 20px;">
            <div style="flex:1;"><label style="font-weight:bold; font-size:0.9rem; color:#8C7B70;">№ Накладної</label><input type="text" id="pn_doc" class="form-control" required placeholder="Напр. 001"></div>
            <div style="flex:2;"><label style="font-weight:bold; font-size:0.9rem; color:#8C7B70;">Постачальник</label><input type="text" id="pn_supplier" class="form-control" required placeholder="Напр. ФОП Іванов"></div>
        </div>
        <table style="margin-bottom: 10px; background: #FFF; border-radius: 8px; border: 1px solid #EFECE6;">
            <thead><tr><th style="width: 20%;">Артикул</th><th style="width: 45%;">Товар / Сировина</th><th style="width: 15%;">К-сть</th><th style="width: 15%;">Сума (грн)</th><th style="width: 5%;"></th></tr></thead>
            <tbody id="pn-body">{pn_rows}</tbody>
        </table>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 15px;">
            <button onclick="addPnRow()" class="btn-outline">➕ Додати рядок</button>
            <button onclick="submitPn()" class="btn-submit" style="padding: 12px 25px; font-size: 1.05rem;">💾 Провести накладну</button>
        </div>
    </div>

    <!-- ТАБ 2: СБОРКА -->
    <div id="tab-assembly" class="tab-content">
        <h3 style="margin-bottom: 15px; color: #5C4033;">Акт комплектації боксу</h3>
        <div style="max-width: 500px; background: #F3EFEA; padding: 20px; border-radius: 8px; border: 1px solid #D9CEBF;">
            <div style="margin-bottom: 15px;"><label style="font-weight:bold; font-size:0.9rem; color:#5C4033;">Який бокс збираємо?</label><select id="box_select" class="form-control" style="margin-top: 5px;">{box_options}</select></div>
            <div style="margin-bottom: 20px;"><label style="font-weight:bold; font-size:0.9rem; color:#5C4033;">Кількість зібраних боксів</label><input type="number" id="box_qty" class="form-control" value="1" min="1" style="margin-top: 5px;"></div>
            <button onclick="assembleBox(this)" class="btn-submit" style="background: #4CAF50; width: 100%; font-size: 1.05rem;">⚙️ Зібрати та Провести в облік</button>
        </div>
    </div>

    <!-- ТАБ 3: СПЕЦИФИКАЦИЯ -->
    <div id="tab-specs" class="tab-content">
        <div style="display: flex; gap: 15px; margin-bottom: 20px; background: #F3EFEA; padding: 15px; border-radius: 8px;">
            <div style="flex:1;"><label style="font-weight:bold; font-size:0.9rem;">Артикул готового боксу</label><input type="text" id="spec_box_art" class="form-control" placeholder="Напр. BOX-05"></div>
            <div style="flex:2;"><label style="font-weight:bold; font-size:0.9rem;">Назва готового боксу</label><input type="text" id="spec_box_name" class="form-control" placeholder="Подарунковий набір Максимум"></div>
        </div>
        <table style="margin-bottom: 10px; border: 1px solid #EFECE6;">
            <thead><tr><th style="width: 25%;">Арт. Сировини</th><th style="width: 50%;">Назва Сировини</th><th style="width: 25%;">Норма (шт/м)</th></tr></thead>
            <tbody id="spec-body">{spec_rows}</tbody>
        </table>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 15px;">
            <button onclick="addSpecRow()" class="btn-outline">➕ Додати рядок</button>
            <button onclick="saveSpecification(this)" class="btn-submit" style="padding: 12px 25px; font-size: 1.05rem; background: #5C4033;">📑 Зберегти Специфікацію</button>
        </div>
    </div>

    <!-- ТАБ 4: ВЫДАТКИ -->
    <div id="tab-vydatky" class="tab-content">
        <form id="form-vydatky" style="max-width: 500px;">
            <label>Категорія</label><select id="v_cat" class="form-control" style="margin-bottom: 15px;"><option>Логістика (НП)</option><option>Реклама</option><option>Оренда/Сервіси</option><option>Канцтовари</option></select>
            <label>Сума (грн)</label><input type="number" step="0.01" id="v_sum" class="form-control" style="margin-bottom: 15px;" required>
            <label>Коментар</label><input type="text" id="v_com" class="form-control" style="margin-bottom: 20px;">
            <button type="submit" class="btn-submit" style="background: #A35D5D; width: 100%;">Зафіксувати витрату</button>
        </form>
    </div>
    """
    
    scripts = """
    <script>
        let nomData = {}; 
        window.onload = async function() {
            try {
                let res = await fetch('/api/nomenclature');
                let data = await res.json();
                let dl = document.getElementById('nomenclature-list');
                data.forEach(item => {
                    nomData[item.article] = item.name;
                    let opt = document.createElement('option');
                    opt.value = item.article; opt.text = item.name; dl.appendChild(opt);
                });
            } catch(e) {}
        };
        function smartFillRow(input) { let art = input.value.trim(); if(nomData[art]) { input.closest('tr').querySelector('.i-name').value = nomData[art]; } }
        function smartFillRowSpec(input) { let art = input.value.trim(); if(nomData[art]) { input.closest('tr').querySelector('.s-name').value = nomData[art]; } }
        function clearRow(btn) { let tr = btn.closest('tr'); tr.querySelector('.i-art').value = ""; tr.querySelector('.i-name').value = ""; tr.querySelector('.i-qty').value = ""; tr.querySelector('.i-sum').value = ""; }
        function addPnRow() { const tbody = document.getElementById('pn-body'); const tr = document.createElement('tr'); tr.innerHTML = `<td><input type="text" class="i-art form-control" list="nomenclature-list" onchange="smartFillRow(this)" placeholder="Артикул"></td><td><input type="text" class="i-name form-control" placeholder="Назва товару"></td><td><input type="number" class="i-qty form-control" placeholder="0"></td><td><input type="number" step="0.01" class="i-sum form-control" placeholder="0.00"></td><td style="text-align:center;"><button type="button" onclick="clearRow(this)" style="padding: 4px 8px; background: #FFDDDD; border: none; border-radius: 4px; cursor: pointer;">❌</button></td>`; tbody.appendChild(tr); }
        function addSpecRow() { const tbody = document.getElementById('spec-body'); const tr = document.createElement('tr'); tr.innerHTML = `<td><input type="text" class="s-art form-control" list="nomenclature-list" onchange="smartFillRowSpec(this)" placeholder="Арт. сировини"></td><td><input type="text" class="s-name form-control" placeholder="Назва сировини"></td><td><input type="number" step="0.01" class="s-qty form-control" placeholder="Норма"></td>`; tbody.appendChild(tr); }
        function openTab(evt, tabName) { document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active')); document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active')); document.getElementById(tabName).classList.add('active'); evt.currentTarget.classList.add('active'); }
        async function submitPn() { const docNum = document.getElementById('pn_doc').value; const supplier = document.getElementById('pn_supplier').value; if(!docNum || !supplier) return alert("Заповніть номер накладної!"); const rows = document.querySelectorAll('#pn-body tr'); const items = []; rows.forEach(row => { const art = row.querySelector('.i-art').value.trim(); const name = row.querySelector('.i-name').value.trim(); const qty = row.querySelector('.i-qty').value; const sum = row.querySelector('.i-sum').value; if(art && name && qty && sum) { items.push({ article: art, name: name, qty: parseInt(qty), total_sum: parseFloat(sum) }); } }); if(items.length === 0) return alert("Заповніть хоча б один рядок!"); try { const response = await fetch('/add-prichid-bulk', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ doc_number: docNum, supplier: supplier, items: items }) }); if(response.ok) { alert('Накладну успішно проведено!'); window.location.reload(); } } catch (err) { alert('Помилка зєднання.'); } }
        async function saveSpecification(btn) { const boxArt = document.getElementById('spec_box_art').value.trim(); const boxName = document.getElementById('spec_box_name').value.trim(); if(!boxArt || !boxName) return alert("Введіть Артикул та Назву!"); const rows = document.querySelectorAll('#spec-body tr'); const components = []; rows.forEach(row => { const cArt = row.querySelector('.s-art').value.trim(); const cName = row.querySelector('.s-name').value.trim(); const qty = row.querySelector('.s-qty').value; if(cArt && cName && qty) { components.push({ c_art: cArt, c_name: cName, qty: parseFloat(qty) }); } }); if(components.length === 0) return alert("Додайте компоненти!"); btn.innerText = "⏳ Зберігаємо..."; try { const response = await fetch('/api/save-specification', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ box_art: boxArt, box_name: boxName, components: components }) }); if(response.ok) { alert('Специфікацію створено!'); window.location.reload(); } } catch (err) { alert('Помилка зєднання.'); } finally { btn.innerText = "📑 Зберегти Специфікацію"; } }
        async function assembleBox(btn) { const boxSelect = document.getElementById('box_select'); const box_id = boxSelect.value; if(!box_id || boxSelect.options[boxSelect.selectedIndex].disabled) return alert("Оберіть існуючий бокс!"); const qty = document.getElementById('box_qty').value; btn.innerText = "⏳ Створюємо..."; try { const response = await fetch('/api/assemble', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ box_id: box_id, qty: parseInt(qty) }) }); const result = await response.json(); if(result.status === "success") { alert('Успішно! Сировину списано.'); } else { alert('Помилка: ' + result.message); } } catch (err) { alert('Помилка зєднання.'); } finally { btn.innerText = "⚙️ Зібрати та Провести в облік"; } }
        document.getElementById('form-vydatky').addEventListener('submit', async (e) => { e.preventDefault(); const data = { category: document.getElementById('v_cat').value, sum: parseFloat(document.getElementById('v_sum').value), comment: document.getElementById('v_com').value, order_id: "" }; try { const response = await fetch('/add-vydatky', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) }); if(response.ok) { alert('Витрату зафіксовано!'); e.target.reset(); } } catch (err) {} });
    </script>
    """
    return base_layout("Облік", content, "accounting", extra_scripts=scripts)

@app.get("/clients", response_class=HTMLResponse)
def get_clients_page(): return base_layout("Клієнти", "<h1>👥 База клієнтів</h1><div class='card'>В розробці</div>", "clients")
@app.get("/novaposhta", response_class=HTMLResponse)
def get_novaposhta_page(): return base_layout("Нова Пошта", "<h1>🚚 Нова Пошта</h1><div class='card'>В розробці</div>", "novaposhta")
@app.get("/messages", response_class=HTMLResponse)
def get_messages_page(): return base_layout("Повідомлення", "<h1>💬 Повідомлення</h1><div class='card'>В розробці</div>", "messages")

# --- API МАРШРУТИ ---
@app.get("/api/nomenclature")
def get_nomenclature():
    try:
        sheet = get_google_sheet("Прихід")
        rows = sheet.get_all_values()
        items = {}
        if len(rows) > 1:
            for r in rows[1:]:
                if len(r) >= 4:
                    art, name = r[2], r[3] 
                    if art and art not in items: items[art] = name
        return [{"article": k, "name": v} for k, v in items.items()]
    except: return []

@app.post("/api/save-specification")
def api_save_specification(req: SpecificationRequest):
    rows_to_insert = [[req.box_art, req.box_name, comp.c_art, comp.c_name, str(comp.qty)] for comp in req.components]
    try:
        add_specification_rows(rows_to_insert)
        return {"status": "success"}
    except Exception as e: return {"status": "error", "message": str(e)}

@app.post("/api/assemble")
def api_assemble(req: AssembleRequest):
    recipes = get_specs_from_sheet()
    if req.box_id not in recipes: return {"status": "error", "message": "Специфікацію не знайдено"}
    recipe = recipes[req.box_id]
    date_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    doc_num = f"АКТ-ЗБІРКИ-{int(datetime.now().timestamp())}"
    try:
        add_prichid_bulk([[date_str, doc_num, recipe["article"], f"{recipe['name']} (Зібрано власно)", str(req.qty), "0", "Власне виробництво", "0"]])
        vydatky_rows = [[date_str, "Виробництво", doc_num, "", comp["article"], comp["name"], str(comp["qty"] * req.qty), "0", "0", "0"] for comp in recipe["components"]]
        add_vitraty_bulk(vydatky_rows)
        return {"status": "success"}
    except Exception as e: return {"status": "error", "message": str(e)}

@app.post("/add-order")
def add_order(order: Order):
    order_data = order.dict()
    order_data["date"] = datetime.now().strftime("%d.%m.%Y %H:%M")
    order_data["status"] = "Нове замовлення"
    save_order_to_sheet(order_data)
    return {"status": "success", "message": "Замовлення прийнято"}

@app.post("/update-order")
def update_order_route(data: OrderUpdate):
    update_order_in_sheet(data.row_id, data.status, data.ttn)
    return {"status": "success"}

@app.post("/add-prichid-bulk")
def add_prichid_bulk_route(data: BulkPrichid):
    date_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    rows_to_insert = [[date_str, data.doc_number, item.article, item.name, str(item.qty), str(item.total_sum), data.supplier, str(round(item.total_sum / item.qty, 2) if item.qty > 0 else 0)] for item in data.items]
    add_prichid_bulk(rows_to_insert)
    return {"status": "success"}

@app.post("/add-vydatky")
def add_vydatky_route(data: VydatkyData):
    add_vydatky({"date": datetime.now().strftime("%d.%m.%Y %H:%M"), "category": data.category, "sum": str(data.sum), "comment": data.comment, "order_id": data.order_id})
    return {"status": "success"}
