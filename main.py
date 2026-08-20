from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import save_order_to_sheet
from datetime import datetime

app = FastAPI()

# НАСТРОЙКИ CORS — это нужно, чтобы ваш сайт мог отправлять данные на сервер
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешает запросы с любого сайта
    allow_credentials=True,
    allow_methods=["*"],  # Разрешает все типы запросов (POST, GET и т.д.)
    allow_headers=["*"],  # Разрешает все заголовки
)

# Модель данных, которые приходят с сайта
class Order(BaseModel):
    name: str
    phone: str
    pet: str
    city: str
    warehouse: str
    product: str

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Velmora CRM API runs smoothly!"}

@app.post("/add-order")
def add_order(order: Order):
    # Добавляем текущую дату
    order_data = order.dict()
    order_data["date"] = datetime.now().strftime("%d.%m.%Y %H:%M")
    order_data["status"] = "Новий"
    
    # Сохраняем в таблицу
    save_order_to_sheet(order_data)
    
    return {"status": "success", "message": "Замовлення прийнято"}
