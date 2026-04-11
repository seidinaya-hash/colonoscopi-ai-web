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
st.set_page_config(page_title="ColoRisk AI Portal", layout="centered")

if 'auth' not in st.session_state:
    st.session_state['auth'] = False

service = get_gdrive_service()

# ОКНО ВХОДА (ПЕРВАЯ СТРАНИЦА)
if not st.session_state['auth']:
    # Блок заголовка с логотипом
    col_title = st.columns([1, 4])
    with col_title:
        st.title("ColoRisk AI")

    # Описание проекта
    st.markdown("""
    **ColoRisk AI** обеспечивает поддержку принятия решений в режиме реального времени — 
    подсвечивает подозрительные участки на видео колоноскопии и рассчитывает примерный размер патологий.
    """)

    # Демонстрационное изображение
    st.write("---")
    st.subheader("Пример работы программы")
    if os.path.exists("demo.jpg"):
        st.image("demo.jpg", caption="Пример детекции и автоматического анализа патологий", use_container_width=True)
    else:
        st.info("Загрузите файл demo.jpg в корневой каталог для отображения примера.")
    
    st.write("---")
    
    # Форма авторизации
    st.subheader("Авторизация для медицинского персонала")
    auth_pass = st.text_input("Введите код доступа", type="password")
    if st.button("Войти в систему"):
        if auth_pass == "врач2024":
            st.session_state['auth'] = True
            if service:
                write_log(service, "ВХОД: Пользователь авторизован")
            st.rerun()
        else:
            st.error("Неверный код доступа")
    st.stop()

# ОСНОВНОЙ ИНТЕРФЕЙС (ПОСЛЕ ВХОДА)
st.title("ColoRisk: Аналитическая панель")
st.write("Загрузите файл для проведения компьютерного анализа.")

if st.sidebar.button("Выйти из системы"):
    st.session_state['auth'] = False
    st.rerun()

uploaded_file = st.file_uploader("Выберите файл", type=['png', 'jpg', 'jpeg', 'mp4', 'mov', 'avi'])

if uploaded_file and service:
    file_name = uploaded_file.name
    is_image = uploaded_file.type.startswith('image')
    
    with st.spinner("Передача данных в систему анализа..."):
        try:
            file_metadata = {'name': file_name, 'parents': [INPUT_ID]}
            media = MediaIoBaseUpload(io.BytesIO(uploaded_file.getbuffer()), mimetype=uploaded_file.type, resumable=True)
            service.files().create(body=file_metadata, media_body=media, fields='id', supportsAllDrives=True).execute()
            write_log(service, f"ЗАГРУЗКА: {file_name} (Тип: {'Изображение' if is_image else 'Видео'})")
            
            status_text = st.empty()
            progress_bar = st.progress(0)
            found = False

            # Ожидание результата (до 300 итераций для длинных видео)
            for i in range(300):
                if is_image:
                    target_name = file_name
                else:
                    target_name = f"REPORT_{file_name}.zip"

                query = f"'{OUTPUT_ID}' in parents and name = '{target_name}' and trashed = false"
                results = service.files().list(q=query, fields='files(id, name)', supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
                items = results.get('files', [])
                
                if items:
                    result_file = items[0]
                    status_text.empty()
                    progress_bar.empty()
                    
                    request = service.files().get_media(fileId=result_file['id'])
                    file_data = request.execute()
                    
                    if is_image:
                        st.success("Анализ изображения завершен")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write("Исходный файл")
                            st.image(uploaded_file)
                        with col2:
                            st.write("Результат ИИ")
                            st.image(file_data)
                        write_log(service, f"ГОТОВО: Изображение {file_name} обработано")
                    else:
                        st.success("Глубокий анализ видео и формирование отчета завершены")
                        st.info("Сформированный архив содержит: обработанное видео, выборку ключевых кадров и текстовую документацию.")
                        st.download_button(
                            label="Скачать архив результатов (ZIP)",
                            data=file_data,
                            file_name=f"Report_AI_{file_name}.zip",
                            mime="application/zip"
                        )
                        write_log(service, f"ГОТОВО: Видео-отчет {file_name} выдан пользователю")
                    
                    # Удаление временного файла из выходной папки Диска
                    try:
                        service.files().delete(fileId=result_file['id'], supportsAllDrives=True).execute()
                    except:
                        pass
                    
                    found = True
                    break
                
                time.sleep(10)
                # Визуальное обновление прогресса (до 100%)
                progress_val = min((i + 1) / 100, 1.0)
                progress_bar.progress(progress_val)
                status_text.info("Выполняется сегментация и расчет параметров патологий. Пожалуйста, подождите...")

            if not found:
                st.error("Превышено время ожидания. Проверьте статус сервера обработки.")
        except Exception as e:
            st.error(f"Системная ошибка: {e}")

# Секция мониторинга
st.write("---")
with st.expander("Системный журнал"):
    adm_pass = st.text_input("Введите пароль доступа к логам", type="password")
    if adm_pass == "1234":
        if service:
            _, logs = get_log_content(service)
            if logs:
                st.text_area("Журнал операций", logs, height=300)
            else:
                st.write("Записи отсутствуют.")
