import streamlit as st
import time
import io
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

# Твои актуальные ID папок на Общем диске
INPUT_ID = "1VqFdKOKc0obTgoLNk1cFbDAd6SFOQvXf"
OUTPUT_ID = "1cOcjJ0SeImKCk0FW4PZ58pVbdBwTjrCD"

st.set_page_config(page_title="AI-ColoScan Portal", page_icon="🩺")

st.title("AI-ColoScan: Анализ видео")
st.write("Загрузите видео колоноскопии. Система обработает его с помощью ИИ и вернет результат.")

uploaded_file = st.file_uploader("Выберите видео файл (MP4)", type=['mp4', 'mov', 'avi'])

if uploaded_file:
    service = get_gdrive_service()
    if service:
        file_name = uploaded_file.name
        
        # 1. Загрузка файла на Google Drive (Общий диск)
        with st.spinner("Загрузка видео в облако..."):
            try:
                file_metadata = {
                    'name': file_name,
                    'parents': [INPUT_ID]
                }
                
                media = MediaIoBaseUpload(
                    io.BytesIO(uploaded_file.getbuffer()), 
                    mimetype='video/mp4', 
                    resumable=True
                )
                
                # Загружаем с флагом supportsAllDrives для Общих дисков
                uploaded_drive_file = service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id',
                    supportsAllDrives=True
                ).execute()
                
                st.success("Видео успешно загружено. ИИ приступает к анализу...")
            except Exception as e:
                st.error(f"Ошибка при загрузке: {e}")
                st.stop()

        # 2. Ожидание результата из папки finished
        st.divider()
        status_text = st.empty()
        progress_bar = st.progress(0)
        
        found = False
        # Проверяем папку каждые 10 секунд в течение 20 минут
        for i in range(120):
            try:
                query = f"'{OUTPUT_ID}' in parents and name = '{file_name}' and trashed = false"
                results = service.files().list(
                    q=query, 
                    spaces='drive', 
                    fields='files(id, name)',
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True
                ).execute()
                
                items = results.get('files', [])
                
                if items:
                    result_file = items[0]
                    status_text.success("Анализ завершен! Загружаем результат...")
                    st.balloons()
                    
                    # Скачиваем готовое видео
                    request = service.files().get_media(fileId=result_file['id'])
                    file_data = request.execute()
                    
                    # Показываем видео на сайте
                    st.video(file_data)
                    
                    # Кнопка скачивания
                    st.download_button(
                        label="Скачать обработанное видео",
                        data=file_data,
                        file_name=f"analyzed_{file_name}",
                        mime="video/mp4"
                    )
                    found = True
                    break
                
                # Обновление прогресса
                time.sleep(10)
                progress_val = min((i + 1) / 60, 1.0) # Визуальный прогресс на 10 минут
                progress_bar.progress(progress_val)
                status_text.info(f"ИИ обрабатывает видео... Прошло {i*10} сек. Не закрывайте страницу.")
                
            except Exception as e:
                st.warning(f"Ожидание обновления данных... ({e})")
                time.sleep(5)

        if not found:
            st.error("Время ожидания истекло. Проверьте, запущен ли Google Colab.")
