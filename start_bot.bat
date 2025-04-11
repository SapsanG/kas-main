@echo off
setlocal enabledelayedexpansion

:: Путь к Python и основному файлу бота
set PYTHON_PATH=python
set BOT_SCRIPT=%~dp0app\main.py

:: Лог-файл для записи событий
set LOG_FILE=%~dp0logs\bot_restart_log.txt

:: Создание директории для логов, если она не существует
if not exist "%~dp0logs" mkdir "%~dp0logs"

:loop
echo [%date% %time%] Запуск бота... >> "%LOG_FILE%"
%PYTHON_PATH% "%BOT_SCRIPT%"

:: Проверка кода выхода
if %errorlevel% neq 0 (
    echo [%date% %time%] Бот завершился с ошибкой. Перезапуск через 5 секунд... >> "%LOG_FILE%"
    timeout /t 5 >nul
    goto loop
)

echo [%date% %time%] Бот завершил работу нормально. >> "%LOG_FILE%"
pause