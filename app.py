import streamlit as st

st.set_page_config(page_title="Colonoscopi AI Portal")
st.title("Colonoscopi AI: Портал загрузки")
st.write("Приложение запущено. Ожидается настройка ключей доступа к Google Drive.")

uploaded_file = st.file_uploader("Выберите видео файл", type=['mp4', 'mov'])

if uploaded_file:
    st.info(f"Файл {uploaded_file.name} успешно загружен в память приложения.")
