@echo off
REM Quick start script for PDF Upload Streamlit App

echo Installing dependencies...
pip install -r requirements.txt

echo.
echo ✅ Installation complete!
echo.
echo Starting Streamlit app...
echo.
streamlit run app.py

pause
