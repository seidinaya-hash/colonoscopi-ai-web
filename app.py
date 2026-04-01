import streamlit as st
from ultralytics import YOLO
import cv2
import tempfile
import os

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="AI-ColoScan PRO", layout="wide")

# CSS для дизайна
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #e6edf3; }
    
    /* ЦЕНТРИРОВАНИЕ ТЕКСТА НАД ВИДЕО */
    .img-label {
        text-align: center;
        font-size: 18px;
        font-weight: 700;
        margin-bottom: 8px;
        color: #ffffff;
        display: block;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* КАРТОЧКИ РЕЗУЛЬТАТОВ */
    .custom-card {
        background-color: #1c2533;
        border: 2px solid #3b82f6;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        margin-top: 20px;
    }
    .custom-label { color: #94a3b8; font-size: 14px; font-weight: 600; text-transform: uppercase; display: block; }
    .custom-value { color: #ffffff; font-size: 28px; font-weight: 900; display: block; }

    .block-container { padding-top: 2rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- ШАПКА ---
st.title("🩺 AI-ColoScan: Clinical Video Analysis")
st.write("Precision diagnostic support powered by YOLOv8 & Kvasir dataset")

# --- ЗАГРУЗКА МОДЕЛИ ---
@st.cache_resource
def load_yolo_model():
    return YOLO('kvasir+polypDB.pt')

model = load_yolo_model()

# --- ИНТЕРФЕЙС ДИАГНОСТИКИ ---
uploaded_file = st.file_uploader("Upload Endoscopy Video", type=['mp4', 'mov', 'avi'], label_visibility="collapsed")

if uploaded_file:
    # Сохраняем загруженное видео во временный файл
    tfile = tempfile.NamedTemporaryFile(delete=False)
    tfile.write(uploaded_file.read())
    
    # Сетка 1x2 для видео
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="img-label">Source Video</div>', unsafe_allow_html=True)
        st.video(tfile.name)

    with col2:
        st.markdown('<div class="img-label">AI Processed Analysis</div>', unsafe_allow_html=True)
        
        # Обработка видео
        cap = cv2.VideoCapture(tfile.name)
        width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps    = int(cap.get(cv2.CAP_PROP_FPS))
        
        # Временный файл для результата
        out_path = "processed_output.mp4"
        # Используем кодек avc1 (H.264) для совместимости с браузерами
        fourcc = cv2.VideoWriter_fourcc(*'avc1') 
        out = cv2.VideoWriter(out_path, fourcc, fps, (width, height))
        
        status_text = st.empty()
        progress_bar = st.progress(0)
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_count = 0
        polyp_found = False

        with st.spinner('AI is analyzing frames...'):
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Запуск модели
                results = model.predict(frame, conf=0.4, verbose=False)
                
                # Если хоть один объект найден
                if len(results[0].boxes) > 0:
                    polyp_found = True
                
                # Отрисовка
                annotated_frame = results[0].plot()
                out.write(annotated_frame)
                
                frame_count += 1
                progress_bar.progress(frame_count / total_frames)

            cap.release()
            out.release()
            progress_bar.empty()

        # Показываем результат
        if os.path.exists(out_path):
            st.video(out_path)
            
            # Итоговая карточка
            if polyp_found:
                st.error("Diagnostic Result: Potential Polyp Detected")
            else:
                st.success("Diagnostic Result: No Polyps Detected")

            # Детализация
            m1, m2 = st.columns(2)
            with m1:
                st.markdown(f'''<div class="custom-card"><span class="custom-label">Status</span>
                            <span class="custom-value">{"POSITIVE" if polyp_found else "NEGATIVE"}</span></div>''', unsafe_allow_html=True)
            with m2:
                st.markdown(f'''<div class="custom-card"><span class="custom-label">Confidence</span>
                            <span class="custom-value">{"High" if polyp_found else "N/A"}</span></div>''', unsafe_allow_html=True)
            
            # Кнопка скачивания
            with open(out_path, "rb") as file:
                st.download_button(label="Download Processed Video", data=file, file_name="ai_analysis.mp4")
else:
    st.info("Please upload an endoscopic video (5-10 sec) to start the clinical analysis.")

# Подвал
st.markdown("---")
st.caption("Disclaimer: This AI system is for educational/research purposes only and should not be used as a primary diagnostic tool.")
