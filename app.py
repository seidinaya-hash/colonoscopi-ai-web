import streamlit as st
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials
import os
import time

# Функция авторизации через Secrets
def get_gdrive():
    try:
        scope = ['https://www.googleapis.com/auth/drive']
        gcp_info = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(gcp_info, scope)
        gauth = GoogleAuth()
        gauth.credentials = creds
        return GoogleDrive(gauth)
    except Exception as e:
        st.error(f"Ошибка авторизации: {e}")
        return None

# Идентификаторы ваших папок
INPUT_ID = "1VqFdKOKc0obTgoLNk1cFbDAd6SFOQvXf"
OUTPUT_ID = "1cOcjJ0SeImKCk0FW4PZ58pVbdBwTjrCD"

st.set_page_config(page_title="AI-ColoScan Portal")

st.title("AI-ColoScan: Анализ видео")
st.write("Загрузите видео эндоскопии. Система передаст файл в Google Colab для обработки нейросетью YOLO.")

uploaded_file = st.file_uploader("Выберите видео файл (MP4)", type=['mp4', 'mov', 'avi'])

if uploaded_file:
    drive = get_gdrive()
    if drive:
        file_name = uploaded_file.name

        
        # 1. Загрузка файла на Google Drive
        with st.spinner("Отправка видео в облачное хранилище..."):
            with open("temp_in.mp4", "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Создаем структуру файла
            file_metadata = {
                'title': file_name, 
                'parents': [{'id': INPUT_ID}]
            }
            
            file_drive = drive.CreateFile(file_metadata)
            file_drive.SetContentFile("temp_in.mp4")
            
            # ВАЖНО: добавляем параметры поддержки дисков и загрузки
            file_drive.Upload(param={'supportsAllDrives': True}) 
            
            st.success("Видео загружено. Ожидайте завершения анализа в Google Colab.")
        
       

        # 2. Ожидание результата
        st.divider()
        status_text = st.empty()
        status_text.info("Поиск обработанного файла. Это может занять несколько минут...")
        
        found = False
        # Цикл проверки папки finished (максимум 20 минут)
        for i in range(120): 
            # Запрос к API Google Drive для поиска файла по имени в папке finished
            query = f"'{OUTPUT_ID}' in parents and title = '{file_name}' and trashed=false"
            file_list = drive.ListFile({'q': query}).GetList()
            
            if file_list:
                result_file = file_list[0]
                status_text.success("Анализ завершен. Видео готово к просмотру.")
                
                # Скачивание результата во временный файл
                result_file.GetContentFile("result_out.mp4")
                
                # Отображение видео в интерфейсе
                st.video("result_out.mp4")
                
                # Кнопка для скачивания пользователем
                with open("result_out.mp4", "rb") as v_file:
                    st.download_button(
                        label="Скачать обработанное видео",
                        data=v_file,
                        file_name=f"analyzed_{file_name}",
                        mime="video/mp4"
                    )
                found = True
                break
            
            # Пауза перед следующей проверкой
            time.sleep(10)
            if i % 2 == 0:
                status_text.warning(f"Обработка продолжается. Пожалуйста, не закрывайте страницу. Прошло {i*10} секунд.")

        if not found:
            st.error("Время ожидания истекло. Убедитесь, что скрипт в Google Colab запущен и имеет доступ к интернету.")
