#!/bin/bash

# Проверка аргумента
if [[ "$1" != "main" && "$1" != "anomaly" ]]; then
  echo "Usage: $0 [main|anomaly]"
  exit 1
fi

# Названия файлов и скриптов
NAME="$1"
SCRIPT="${NAME}.py"
LOG_DIR="${NAME}_logs"
PID_FILE="${NAME}.pid"

cd ~/tg_sender/ || exit 1
mkdir -p "$LOG_DIR"
source ./venv/bin/activate

# Найдём номер следующего лога
i=0
while [[ -f "${LOG_DIR}/${i}.log" ]]; do
  ((i++))
done

# Запускаем и сохраняем PID
nohup python "$SCRIPT" > "${LOG_DIR}/${i}.log" 2>&1 &
echo $! > "$PID_FILE"
