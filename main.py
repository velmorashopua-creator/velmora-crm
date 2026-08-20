import streamlit as st
import pandas as pd
from database import get_google_sheet

# Настройка страницы
st.set_page_config(page_title="Velmora CRM — Главная", page_icon="📦", layout="wide")

st.title("📦 Velmora CRM | Главная")
st.markdown("Управление заказами и актуальная база данных в реальном времени")

# Функция загрузки реальных данных из Google Таблицы
@st.cache_data(ttl=10) # обновление каждые 10 секунд
def load_real_data():
    try:
        sheet = get_google_sheet()
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Ошибка подключения к таблице: {e}")
        return pd.DataFrame()

df = load_real_data()

if not df.empty:
    # --- БЛОК С ЦИФРАМИ (МЕТРИКИ) ---
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(label="📥 Всего заказов", value=len(df))

    with col2:
        # Проверяем, есть ли колонка со статусом
        if "Статус" in df.columns:
            new_orders = len(df[df["Статус"] == "Новий"])
            st.metric(label="🔥 Новые заявки", value=new_orders)
        else:
            st.metric(label="🔥 Новые заявки", value=0)

    with col3:
        if "Статус" in df.columns:
            sent_orders = len(df[df["Статус"] == "Відправлено"])
            st.metric(label="🚚 Отправлено", value=sent_orders)
        else:
            st.metric(label="🚚 Отправлено", value=0)

    with col4:
        if "Статус" in df.columns:
            done_orders = len(df[df["Статус"] == "Виконано"])
            st.metric(label="💰 Выполнено", value=done_orders)
        else:
            st.metric(label="💰 Выполнено", value=0)

    st.markdown("---")

    # --- ТАБЛИЦА ЗАКАЗОВ ---
    st.subheader("📋 Список заказов")
    
    # Кнопка обновления данных
    if st.button("🔄 Обновить данные"):
        st.cache_data.clear()
        st.rerun()

    st.dataframe(df, use_container_width=True)
else:
    st.warning("Таблица пока пуста или данные загружаются...")
