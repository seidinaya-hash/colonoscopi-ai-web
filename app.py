import streamlit as st
import time
import io
from datetime import datetime
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

# Константы путей
INPUT_ID = "1VqFdKOKc0obTgoLNk1cFbDAd6SFOQvXf"
OUTPUT_ID = "1cOcjJ0SeImKCk0FW4PZ58pVbdBwTjrCD"
METRICS_ID = "1fIwirl-vegbT61HovVHGEJukxGHwdJH2"

def update_metrics(service, action_type):
    """Записывает лог посещения или обработки видео"""
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{now} - {action_type}\n"
        
        query = f"'{METRICS_ID}' in parents and name = 'logs.txt' and trashed = false"
        results = service.files().list(q=query, supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
        items = results.get('files', [])

        if items:
            file_id = items[0]['id']
            # Получаем текущее содержимое
            content = service.files().get_media(fileId=file_id).execute().decode('utf-8')
            new_content = content + log_entry
            media = MediaIoBaseUpload(io.BytesIO(new_content.encode('utf-8')), mimetype='text/plain')
            service.files().update(fileId=file_id, media_body=media, supportsAllDrives=True).execute()
        else:
            # Создаем файл, если его нет
            file_metadata = {'name': 'logs.txt', 'parents': [METRICS_ID]}
            media = MediaIoBaseUpload(io.BytesIO(log_entry.encode('utf-8')), mimetype='text/plain')
            service.files().create(body=file_metadata, media_body=media, supportsAllDrives=True).execute()
    except:
        pass

st.set_page_config(page_title="AI-ColoScan Portal", page_icon="🩺")

service = get_gdrive_service()

# Логируем посещение при открытии страницы
if service and 'session_started' not in st.session_state:
    update_metrics(service, "Посещение сайта")
    st.session_state['session_started'] = True

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
                    st.success("Анализ успешно завершен.")
                    
                    # Логируем успешную обработку
                    update_metrics(service, f"Успешный анализ: {file_name}")

                    request = service.files().get_media(fileId=result_file['id'])
                    file_data = request.execute()
                    
                    st.download_button(label="Скачать результат анализа (MP4)", data=file_data, file_name=f"analyzed_{file_name}", mime="video/mp4")

                    # Очистка облака
                    try:
                        service.files().delete(fileId=result_file['id'], supportsAllDrives=True).execute()
                        search_orig = service.files().list(q=f"'{INPUT_ID}' in parents and name = '{file_name}' and trashed = false", fields='files(id)', supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
                        orig_items = search_orig.get('files', [])
                        if orig_items:
                            service.files().delete(fileId=orig_items[0]['id'], supportsAllDrives=True).execute()
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

# --- ПАНЕЛЬ АДМИНИСТРАТОРА (СКРЫТАЯ) ---
st.write("")
with st.expander("Admin Panel"):
    access_key = st.text_input("Ввод ключа", type="password")
    if access_key == "1234": # ЗАМЕНИ НА СВОЙ ПАРОЛЬ
        if service:
            try:
                query = f"'{METRICS_ID}' in parents and name = 'logs.txt' and trashed = false"
                res = service.files().list(q=query, supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
                log_files = res.get('files', [])
                if log_files:
                    logs = service.files().get_media(fileId=log_files[0]['id']).execute().decode('utf-8')
                    st.text_area("Логи системы", logs, height=300)
                    st.download_button("Скачать лог-файл", logs, file_name="coloscan_logs.txt")
                else:
                    st.write("Логов пока нет.")
            except:
                st.write("Ошибка доступа к логам.")
