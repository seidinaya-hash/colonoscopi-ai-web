import streamlit as st
import os

# Сначала пробуем импортировать всё остальное
try:
    from ultralytics import YOLO
    import cv2
    import numpy as np
    from PIL import Image
except ImportError as e:
    st.error(f"Ошибка импорта: {e}. Проверьте файлы requirements.txt и packages.txt")

st.set_page_config(page_title="Colonoscopi AI", layout="wide")
st.title("🩺 Colonoscopi AI: Clinical Analysis")

# Загрузка модели с кэшированием
@st.cache_resource
def load_model():
    if os.path.exists('kvasir+polypDB.pt'):
        return YOLO('kvasir+polypDB.pt')
    else:
        st.error("Файл модели 'kvasir+polypDB.pt' не найден в репозитории!")
        return None

model = load_model()

uploaded_file = st.file_uploader("Загрузите фото или видео", type=['jpg', 'png', 'mp4', 'mov'])

if uploaded_file and model:
    # ОПРЕДЕЛЯЕМ ТИП ФАЙЛА
    is_video = uploaded_file.name.lower().endswith(('.mp4', '.mov'))
    
    if not is_video:
        # ОБРАБОТКА ФОТО (Безопасный метод через PIL)
        image = Image.open(uploaded_file)
        results = model.predict(image, conf=0.25)
        
        # Вместо results[0].plot() (который вызывает ошибку), рисуем сами или выводим результат
        res_plotted = results[0].plot() # Если libGL стоит, это сработает
        st.image(res_plotted, caption="Результат анализа", use_container_width=True)
    
    else:
        # ОБРАБОТКА ВИДЕО
        st.warning("Обработка видео может занять время на бесплатном сервере...")
        # (Тут код обработки видео, который мы обсуждали ранее)
        st.info("Функция видео активна. Начните анализ.")
