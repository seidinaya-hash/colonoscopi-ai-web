import streamlit as st
import time
import io
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# Функция авторизации через Secrets Streamlit
def get_gdrive_service():
    try:
        creds_info = st.secrets["gcp_service_account"]
        creds = service_account.Credentials.from_service_account_info(
            creds_info, 
            scopes=['https://www.googleapis.com/auth/drive']
        )
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        st.error(f"Ошибка авторизации: {e}")
        return None

# ID папок на Общем диске
INPUT_ID = "1VqFdKOKc0obTgoLNk1cFbDAd6SFOQvXf"
OUTPUT_ID = "1cOcjJ0SeImKCk0FW4PZ58pVbdBwTjrCD"
METRICS_ID = "1fIwirl-vegbT61HovVHGEJukxGHwdJH2"

# --- ФУНКЦИИ МЕТРИК С ИСПРАВЛЕННЫМ ВРЕМЕНЕМ ---

def get_log_content(service):
    """Получает id файла логов и его текст"""
    try:
        query = f"'{METRICS_ID}' in parents and name = 'logs.txt' and trashed = false"
        results = service.files().list(q=query, supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
        items = results.get('files', [])
        if items:
            file_id = items[0]['id']
            content = service.files().get_media(fileId=file_id).execute().decode('utf-8')
            return file_id, content
        return None, ""
    except:
        return None, ""

def write_log(service, message):
    """Записывает событие в лог (Время Астаны: UTC+5)"""
    try:
        file_id, old_content = get_log_content(service)
        
        # Коррекция времени: берем UTC и добавляем 5 часов
        astana_time = (datetime.utcnow() + timedelta(hours=5)).strftime("%d.%m.%Y %H:%M:%S")
        
        new_line = f"[{astana_time}] {message}\n"
        full_content = old_content + new_line
        
        media = MediaIoBaseUpload(io.BytesIO(full_content.encode('utf-8')), mimetype='text/plain')
        
        if file_id:
            service.files().update(fileId=file_id, media_body=media, supportsAllDrives=True).execute()
        else:
            file_metadata = {'name': 'logs.txt', 'parents': [METRICS_ID]}
            service.files().create(body=file_metadata, media_body=media, supportsAllDrives=True).execute()
    except:
        pass

# --- ОСНОВНОЙ ИНТЕРФЕЙС ---

st.set_page_config(page_title="AI-ColoScan Portal", page_icon="🩺")

service = get_gdrive_service()

# Логика сессии (записывает визит только один раз за открытие вкладки)
if service and 'session_active' not in st.session_state:
    write_log(service, "ВХОД: Врач открыл портал")
    st.session_state['session_active'] = True

st.title("AI-ColoScan: Анализ видео")
st.write("Загрузите видео колоноскопии для автоматизированного поиска патологий.")

uploaded_file = st.file_uploader("Выберите видео файл (MP4, MOV, AVI)", type=['mp4', 'mov', 'avi'])

if uploaded_file:
    if service:
        file_name = uploaded_file.name
        
        with st.spinner("Загрузка файла в систему..."):
            try:
                file_metadata = {'name': file_name, 'parents': [INPUT_ID]}
                media = MediaIoBaseUpload(io.BytesIO(uploaded_file.getbuffer()), mimetype='video/mp4', resumable=True)
                service.files().create(body=file_metadata, media_body=media, fields='id', supportsAllDrives=True).execute()
                
                # Логируем загрузку
                write_log(service, f"ЗАГРУЗКА: {file_name}")
                st.success("Файл принят. Ожидайте завершения анализа.")
            except Exception as e:
                st.error(f"Ошибка передачи данных: {e}")
                st.stop()

        status_text = st.empty()
        progress_bar = st.progress(0)
        found = False

        for i in range(120):
            try:
                query = f"'{OUTPUT_ID}' in parents and name = '{file_name}' and trashed = false"
                results = service.files().list(q=query, spaces='drive', fields='files(id, name)', supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
                
                items = results.get('files', [])
                if items:
                    result_file = items[0]
                    status_text.empty()
                    progress_bar.empty()
                    
                    # Логируем успешный финиш
                    write_log(service, f"ГОТОВО: Анализ {file_name} завершен")
                    st.success("Анализ успешно завершен.")
                    
                    request = service.files().get_media(fileId=result_file['id'])
                    file_data = request.execute()
                    
                    st.download_button(
                        label="Скачать результат анализа (MP4)", 
                        data=file_data, 
                        file_name=f"analyzed_{file_name}", 
                        mime="video/mp4"
                    )

                    # Очистка
                    try:
                        service.files().delete(fileId=result_file['id'], supportsAllDrives=True).execute()
                        search_orig = service.files().list(q=f"'{INPUT_ID}' in parents and name = '{file_name}' and trashed = false", fields='files(id)', supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
                        orig_items = search_orig.get('files', [])
                        if orig_items:
                            service.files().delete(fileId=orig_items[0]['id'], supportsAllDrives=True).execute()
                        st.info("Файлы удалены из облака после обработки.")
                    except:
                        pass
                    
                    found = True
                    break
                
                time.sleep(10)
                progress_bar.progress(min((i + 1) / 60, 1.0))
                status_text.info("Выполняется инференс модели ИИ. Пожалуйста, ожидайте...")
            except:
                time.sleep(5)

        if not found:
            st.error("Превышено время ожидания.")

# --- АДМИН ПАНЕЛЬ (ТОЛЬКО ЛОГИ И ВРЕМЯ) ---
st.write("---")
with st.expander("Панель управления"):
    password = st.text_input("Пароль", type="password")
    if password == "1234": # Здесь твой пароль
        if service:
            _, logs = get_log_content(service)
            if logs:
                st.text_area("История действий (Время Астаны)", logs, height=400)
                st.download_button("Скачать лог", logs, file_name="logs.txt")
            else:
                st.write("История пуста.")
