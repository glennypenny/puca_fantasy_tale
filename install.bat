@echo off
echo ============================================
echo    Puca - Dark Fantasy Tale Setup
echo ============================================
echo.

:: --- Check for Python ---
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed. Please install it from python.org
    echo IMPORTANT: Check "Add Python to PATH" during installation
    pause
    exit /b
)

:: --- Install ALL required Python packages ---
echo Installing required Python packages...
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install diffusers transformers accelerate peft Pillow requests pywin32 pygame

:: --- Check for Ollama ---
where ollama >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo Ollama is not installed. Downloading and installing...
    powershell -Command "Invoke-WebRequest -Uri 'https://ollama.com/download/OllamaSetup.exe' -OutFile 'OllamaSetup.exe'"
    start /wait OllamaSetup.exe
    del OllamaSetup.exe
)

:: --- Pull the Mistral model (this downloads ~4 GB) ---
echo.
echo Pulling the Mistral model for Ollama (this will take a few minutes)...
ollama pull mistral

:: --- Done ---
echo.
echo ============================================
echo Setup complete!
echo.
echo Before playing, make sure Ollama is running.
echo You can start it from the Start menu or by typing 'ollama serve' in a terminal.
echo Then run: python my_version_of_kawa.py
echo ============================================
pause