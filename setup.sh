#!/bin/bash

# Путь к директории, куда клонирован проект
PROJECT_DIR="."  # можно заменить на путь, например /home/user/project

# --- Проверка и установка Python 3.12 ---
if ! command -v python3.12 &> /dev/null; then
    echo "Python 3.12 не найден. Устанавливаю..."
    sudo apt update
    sudo apt install -y software-properties-common
    sudo add-apt-repository -y ppa:deadsnakes/ppa
    sudo apt update
    sudo apt install -y python3.12 python3.12-venv python3.12-distutils
    echo "Python 3.12 установлен."
fi

# --- Проверка и установка screen ---
if ! command -v screen &> /dev/null; then
    echo "Утилита 'screen' не найдена. Устанавливаю..."
    sudo apt update
    sudo apt install -y screen
    echo "screen установлен."
fi

# Список директорий
mkdir -p "$PROJECT_DIR/anomaly_logs" \
         "$PROJECT_DIR/main_logs" \
         "$PROJECT_DIR/sessions"

# Создание файлов с начальным содержимым
echo "[]" > "$PROJECT_DIR/active.json"
echo "[]" > "$PROJECT_DIR/authorized_users.json"
echo "{}" > "$PROJECT_DIR/auto_reac.json"
echo "{}" > "$PROJECT_DIR/auto_reps.json"
echo "{}" > "$PROJECT_DIR/auto_views.json"
echo "{}" > "$PROJECT_DIR/cache_views.json"
echo "{}" > "$PROJECT_DIR/daily.json"
echo "[]" > "$PROJECT_DIR/emerge.json"
echo "[]" > "$PROJECT_DIR/finished.json"
echo "{}" > "$PROJECT_DIR/last_main_check.json"
echo "[]" > "$PROJECT_DIR/sent.json"

python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

echo "Все файлы и директории созданы. Виртуальное окружение настроено."
