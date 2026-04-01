import streamlit as st
from ultralytics import YOLO
from PIL import Image
import tempfile
import os
import cv2
import numpy as np

# Настройки страницы
st.set_page_config(page_title="Colonoscopi AI Web", layout="wide")

st.title("🩺 Colonoscopi AI Web")
st.write("Клинический анализ видео (Стабильная версия)")

# Загрузка модели
@st.cache_resource
def load_yolo_model():
    return YOLO('kvasir+polypDB.pt')

model = load_yolo_model()

uploaded_file = st.file_uploader("Загрузите видео (5-10 сек)", type=['mp4', 'mov', 'avi'])

if uploaded_file:
    # Сохраняем видео во временный файл
    tfile = tempfile.NamedTemporaryFile(delete=False)
    tfile.write(uploaded_file.read())
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Исходное видео")
        st.video(tfile.name)

    with col2:
        st.subheader("Результат анализа")
        
        cap = cv2.VideoCapture(tfile.name)
        st_frame = st.empty() # Окно для вывода кадров в реальном времени
        
        polyp_detected = False
        
        if st.button("Начать анализ"):
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Делаем предсказание
                results = model.predict(frame, conf=0.5, verbose=False)
                
                # РИСУЕМ РАМКИ ВРУЧНУЮ (БЕЗ .plot()), чтобы не было ошибки libGL
                for result in results:
                    if len(result.boxes) > 0:
                        polyp_detected = True
                        for box in result.boxes:
                            # Получаем координаты
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            # Рисуем рамку силами OpenCV (в headless версии это работает)
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 3)
                            cv2.putText(frame, "POLYP", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)

                # Преобразуем формат из BGR (OpenCV) в RGB (Streamlit)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                st_frame.image(frame_rgb, channels="RGB", use_container_width=True)
            
            cap.release()
            
            if polyp_detected:
                st.error("ВНИМАНИЕ: Обнаружен полип!")
            else:
                st.success("Анализ завершен: Патологий не найдено.")
else:
    st.info("Загрузите видео для начала работы.")
