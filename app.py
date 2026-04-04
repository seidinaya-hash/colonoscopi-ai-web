import streamlit as st
import time
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# Настройка доступа через секреты Streamlit
def get_gdrive_service():
    creds_info = st.secrets["gcp_service_account"]
    creds = service_account.Credentials.from_service_account_info(
        creds_info, 
        scopes=['https://www.googleapis.com/auth/drive']
    )
    return build('drive', 'v3', credentials=creds)

# Ваши ID папок
INPUT_ID = "1VqFdKOKc0obTgoLNk1cFbDAd6SFOQvXf"
OUTPUT_ID = "1cOcjJ0SeImKCk0FW4PZ58pVbdBwTjrCD"

st.set_page_config(page_title="AI-ColoScan Portal")
st.title("AI-ColoScan: Анализ видео")

uploaded_file = st.file_uploader("Выберите видео файл (MP4)", type=['mp4', 'mov', 'avi'])

if uploaded_file:
    service = get_gdrive_service()
    file_name = uploaded_file.name
    
    with st.spinner("Отправка видео в облако..."):
        try:
            # Подготовка метаданных файла
            file_metadata = {
                'name': file_name,
                'parents': [INPUT_ID]
            }
            
            # Подготовка самого файла для передачи
            media = MediaIoBaseUpload(
                io.BytesIO(uploaded_file.getbuffer()), 
                mimetype='video/mp4', 
                resumable=True
            )
            
            # ЗАГРУЗКА: используем supportsAllDrives=True
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id',
                supportsAllDrives=True
            ).execute()
            
            st.success("Видео загружено. Ожидайте завершения анализа в Google Colab.")
            
            # Ожидание результата
            st.divider()
            status_text = st.empty()
            status_text.info("Поиск обработанного файла...")
            
            found = False
            for i in range(120):
                # Поиск файла в папке finished
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
                    status_text.success("Анализ завершен!")
                    st.balloons()
                    
                    # Скачивание файла
                    request = service.files().get_media(fileId=result_file['id'])
                    file_data = request.execute()
                    
                    st.video(file_data)
                    st.download_button(
                        label="Скачать результат",
                        data=file_data,
                        file_name=f"analyzed_{file_name}",
                        mime="video/mp4"
                    )
                    found = True
                    break
                
                time.sleep(10)
                if i % 2 == 0:
                    status_text.warning(f"Обработка в Colab... Прошло {i*10} сек.")
            
            if not found:
                st.error("Превышено время ожидания.")
                
        except Exception as e:
            st.error(f"Произошла ошибка: {str(e)}")
