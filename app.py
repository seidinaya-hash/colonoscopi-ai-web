import streamlit as st
from ultralytics import YOLO
import cv2
import tempfile
import os
import subprocess

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="Colonoscopi AI Web", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #e6edf3; }
    .img-label { text-align: center; font-size: 18px; font-weight: 700; margin-bottom: 8px; color: #ffffff; display: block; text-transform: uppercase; }
    .custom-card { background-color: #1c2533; border: 2px solid #3b82f6; border-radius: 10px; padding: 15px; text-align: center; margin-top: 20px; }
    .custom-label { color: #94a3b8; font-size: 14px; font-weight: 600; text-transform: uppercase; display: block; }
    .custom-value { color: #ffffff; font-size: 28px; font-weight: 900; display: block; }
    </style>
    """, unsafe_allow_html=True)

# --- ШАПКА ---
st.title("🩺 Colonoscopi AI Web")
st.write("Система клинического анализа видео на базе нейросети YOLOv8")

# --- ЗАГРУЗКА МОДЕЛИ ---
@st.cache_resource
def load_yolo_model():
    return YOLO('kvasir+polypDB.pt')

model = load_yolo_model()

uploaded_file = st.file_uploader("Загрузите видео (MP4, MOV, AVI)", type=['mp4', 'mov', 'avi'], label_visibility="collapsed")

if uploaded_file:
    tfile = tempfile.NamedTemporaryFile(delete=False)
    tfile.write(uploaded_file.read())
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="img-label">Исходное видео</div>', unsafe_allow_html=True)
        st.video(tfile.name)

    with col2:
        st.markdown('<div class="img-label">Анализ ИИ (Обработка...)</div>', unsafe_allow_html=True)
        
        cap = cv2.VideoCapture(tfile.name)
        # Уменьшаем размер для стабильности на бесплатном сервере
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        
        # Временный файл для OpenCV (промежуточный)
        temp_out = "temp_result.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
        out = cv2.VideoWriter(temp_out, fourcc, fps, (width, height))
        
        progress_bar = st.progress(0)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_count = 0
        polyp_detected = False

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            
            # Предсказание (conf=0.4 для баланса точности)
            results = model.predict(frame, conf=0.4, verbose=False)
            
            if len(results[0].boxes) > 0:
                polyp_detected = True
            
            annotated_frame = results[0].plot()
            out.write(annotated_frame)
            
            frame_count += 1
            progress_bar.progress(frame_count / total_frames)

        cap.release()
        out.release()
        progress_bar.empty()

        # КОНВЕРТАЦИЯ В H.264 (чтобы видео открылось в браузере)
        # Мы используем ffmpeg, который ты добавила в packages.txt
        final_out = "final_diagnostics.mp4"
        subprocess.call(f"ffmpeg -y -i {temp_out} -c:v libx264 {final_out}", shell=True)

        if os.path.exists(final_out):
            st.video(final_out)
            
            if polyp_detected:
                st.error("Результат: Обнаружены признаки полипа")
            else:
                st.success("Результат: Патологий не обнаружено")

            m1, m2 = st.columns(2)
            with m1:
                st.markdown(f'<div class="custom-card"><span class="custom-label">Статус</span><span class="custom-value">{"ПОЗИТИВНЫЙ" if polyp_detected else "НЕГАТИВНЫЙ"}</span></div>', unsafe_allow_html=True)
            with m2:
                st.markdown(f'<div class="custom-card"><span class="custom-label">Точность ИИ</span><span class="custom-value">{"Высокая" if polyp_detected else "—"}</span></div>', unsafe_allow_html=True)
            
            with open(final_out, "rb") as f:
                st.download_button("Скачать отчет в MP4", f, file_name="colon_analysis.mp4")
else:
    st.info("Пожалуйста, загрузите короткое видео (5-10 сек) для начала анализа.")
