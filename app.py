import streamlit as st
from ultralytics import YOLO
import cv2
import tempfile
import os

# Настройка страницы
st.set_page_config(page_title="AI-ColoScan PRO", layout="wide")

st.title("🩺 AI-ColoScan PRO: Клинический анализ")
st.markdown("Система автоматического поиска полипов на базе нейросети YOLOv8.")

# Загрузка модели
@st.cache_resource # Чтобы модель не перезагружалась при каждом клике
def load_model():
    return YOLO('kvasir+polypDB.pt')

model = load_model()

# Боковая панель
st.sidebar.header("Настройки")
conf_threshold = st.sidebar.slider("Уровень уверенности (Confidence)", 0.1, 1.0, 0.5)

# Загрузка файла
uploaded_video = st.file_uploader("Загрузите видео колоноскопии (MP4, AVI)", type=['mp4', 'avi', 'mov'])

if uploaded_video is not None:
    # Сохраняем загруженный файл во временную папку
    tfile = tempfile.NamedTemporaryFile(delete=False)
    tfile.write(uploaded_video.read())
    
    cap = cv2.VideoCapture(tfile.name)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    st.info(f"Видео загружено. Всего кадров: {total_frames}. Начинаем обработку...")
    
    # Подготовка к записи результата
    output_path = "processed_video.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    # Полоса прогресса
    progress_bar = st.progress(0)
    frame_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        # Предсказание
        results = model.predict(frame, conf=conf_threshold, verbose=False)
        annotated_frame = results[0].plot()
        
        # Запись
        out.write(annotated_frame)
        
        # Обновление прогресса
        frame_count += 1
        progress_bar.progress(frame_count / total_frames)

    cap.release()
    out.release()

    st.success("Обработка завершена!")
    
    # Показ результата
    st.video(output_path)
    
    # Кнопка скачивания
    with open(output_path, "rb") as file:
        st.download_button(label="Скачать результат", data=file, file_name="result.mp4")
