from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from database import save_order_to_sheet

app = FastAPI(title="Velmora CRM API")

# Налаштовуємо CORS, щоб сайт міг відправляти запити на наш сервер
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # На старті дозволяємо запити з усіх джерел
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Схема даних замовлення від клієнта
class OrderSchema(BaseModel):
    name: str
    phone: str
    pet: str = ""
    city: str = ""
    warehouse: str = ""
    product: str = ""

@app.get("/")
def home():
    return {"status": "ok", "message": "Velmora CRM API runs smoothly!"}

@app.post("/api/order")
def create_order(order: OrderSchema):
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        order_data = {
            "date": current_time,
            "name": order.name,
            "phone": order.phone,
            "pet": order.pet,
            "city": order.city,
            "warehouse": order.warehouse,
            "product": order.product,
            "status": "Новий"
        }
        
        save_order_to_sheet(order_data)
        return {"status": "success", "message": "Замовлення успішно збережено!"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))