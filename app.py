import streamlit as st
import time
import io
import os
from PIL import Image
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

# Настройки и авторизация Google Drive
def get_gdrive_service():
    try:
        creds_info = st.secrets["gcp_service_account"]
        creds = service_account.Credentials.from_service_account_info(
            creds_info, 
            scopes=['https://www.googleapis.com/auth/drive']
        )
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        st.error(f"Ошибка авторизации Google: {e}")
        return None

# ID папок на Диске
INPUT_ID = "1VqFdKOKc0obTgoLNk1cFbDAd6SFOQvXf"
OUTPUT_ID = "1cOcjJ0SeImKCk0FW4PZ58pVbdBwTjrCD"
METRICS_ID = "1fIwirl-vegbT61HovVHGEJukxGHwdJH2"

# Функции работы с логами
def get_log_content(service):
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
    try:
        file_id, old_content = get_log_content(service)
        # Установка времени Астаны (UTC+5)
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

# Конфигурация страницы
st.set_page_config(page_title="AI-ColoScan Portal", layout="centered")

# Инициализация состояния входа
if 'auth' not in st.session_state:
    st.session_state['auth'] = False

service = get_gdrive_service()

# Окно входа
if not st.session_state['auth']:
    st.title("Вход в систему AI-ColoScan")
    st.write("Авторизуйтесь для доступа к анализу данных.")
    
    auth_pass = st.text_input("Введите код доступа", type="password")
    if st.button("Войти"):
        if auth_pass == "врач2024":
            st.session_state['auth'] = True
            if service:
                write_log(service, "ВХОД: Пользователь авторизован")
            st.rerun()
        else:
            st.error("Неверный код доступа")
    st.stop()

# Основной интерфейс после входа
st.title("AI-ColoScan: Аналитическая панель")
st.write("Загрузите скан или видео для проведения диагностики.")

if st.sidebar.button("Выйти"):
    st.session_state['auth'] = False
    st.rerun()

uploaded_file = st.file_uploader("Выберите файл", type=['png', 'jpg', 'jpeg', 'mp4', 'mov', 'avi'])

if uploaded_file and service:
    file_name = uploaded_file.name
    is_image = uploaded_file.type.startswith('image')
    
    with st.spinner("Передача файла в систему анализа..."):
        try:
            # Загрузка файла на Диск
            file_metadata = {'name': file_name, 'parents': [INPUT_ID]}
            media = MediaIoBaseUpload(io.BytesIO(uploaded_file.getbuffer()), mimetype=uploaded_file.type, resumable=True)
            service.files().create(body=file_metadata, media_body=media, fields='id', supportsAllDrives=True).execute()
            write_log(service, f"ЗАГРУЗКА: {file_name} (Тип: {'Изображение' if is_image else 'Видео'})")
            
            # Ожидание результата от модели
            status_text = st.empty()
            progress_bar = st.progress(0)
            found = False

            for i in range(120):
                query = f"'{OUTPUT_ID}' in parents and name = '{file_name}' and trashed = false"
                results = service.files().list(q=query, fields='files(id, name)', supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
                items = results.get('files', [])
                
                if items:
                    result_file = items[0]
                    status_text.empty()
                    progress_bar.empty()
                    
                    # Скачивание обработанного файла
                    request = service.files().get_media(fileId=result_file['id'])
                    file_data = request.execute()
                    
                    if is_image:
                        st.success("Анализ изображения завершен")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write("Исходный скан")
                            st.image(uploaded_file)
                        with col2:
                            st.write("Результат анализа")
                            st.image(file_data)
                        write_log(service, f"ГОТОВО: Изображение {file_name} обработано")
                    else:
                        st.success("Анализ видео завершен")
                        st.download_button(
                            label="Скачать проанализированное видео",
                            data=file_data,
                            file_name=f"processed_{file_name}",
                            mime="video/mp4"
                        )
                        write_log(service, f"ГОТОВО: Видео {file_name} обработано")

                    # Автоматическая очистка
                    try:
                        service.files().delete(fileId=result_file['id'], supportsAllDrives=True).execute()
                        search_orig = service.files().list(q=f"'{INPUT_ID}' in parents and name = '{file_name}' and trashed = false", fields='files(id)', supportsAllDrives=True).execute()
                        orig_items = search_orig.get('files', [])
                        if orig_items:
                            service.files().delete(fileId=orig_items[0]['id'], supportsAllDrives=True).execute()
                    except:
                        pass
                    
                    found = True
                    break
                
                time.sleep(10)
                progress_bar.progress(min((i + 1) / 60, 1.0))
                status_text.info("Система обрабатывает данные. Ожидайте...")

            if not found:
                st.error("Таймаут ожидания. Проверьте работу сервера обработки.")
        except Exception as e:
            st.error(f"Системная ошибка: {e}")

# Админ-секция
st.write("---")
with st.expander("Панель администратора"):
    adm_pass = st.text_input("Код администратора", type="password")
    if adm_pass == "1234":
        if service:
            _, logs = get_log_content(service)
            if logs:
                st.text_area("Логи системы", logs, height=300)
            else:
                st.write("История пуста.")
