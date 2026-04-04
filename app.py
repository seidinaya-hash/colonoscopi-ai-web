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
st.write("Загрузите видео колоноскопии для автоматизированного поиска патологий.")

uploaded_file = st.file_uploader("Выберите видео файл (MP4, MOV, AVI)", type=['mp4', 'mov', 'avi'])

if uploaded_file:
    service = get_gdrive_service()
    if service:
        file_name = uploaded_file.name
        
        # 1. Загрузка файла на Google Drive
        with st.spinner("Загрузка файла в систему..."):
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
                
                service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id',
                    supportsAllDrives=True
                ).execute()
                
                st.success("Файл принят. Ожидайте завершения анализа.")
            except Exception as e:
                st.error(f"Ошибка передачи данных: {e}")
                st.stop()

        # 2. Мониторинг готовности результата
        status_text = st.empty()
        progress_bar = st.progress(0)
        
        found = False
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
                    
                    # Очищаем индикаторы прогресса перед показом кнопки
                    status_text.empty()
                    progress_bar.empty()
                    
                    st.success("Анализ успешно завершен.")
                    
                    # Получение данных файла
                    request = service.files().get_media(fileId=result_file['id'])
                    file_data = request.execute()
                    
                    # Кнопка скачивания (строгий стиль)
                    st.download_button(
                        label="Скачать результат анализа (MP4)",
                        data=file_data,
                        file_name=f"analyzed_{file_name}",
                        mime="video/mp4"
                    )
                    
                    found = True
                    break
                
                time.sleep(10)
                progress_val = min((i + 1) / 60, 1.0)
                progress_bar.progress(progress_val)
                status_text.info("Выполняется инференс модели ИИ. Пожалуйста, ожидайте...")
                
            except Exception as e:
                time.sleep(5)

        if not found:
            st.error("Превышено время ожидания ответа от сервера обработки.")
