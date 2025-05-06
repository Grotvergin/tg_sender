#!/bin/bash

cd ~/tg_sender/
mkdir -p main_logs
source ./venv/bin/activate

# Найдём номер следующего лога
i=0
while [[ -f "main_logs/$i.log" ]]; do
  ((i++))
done

# Сохраняем PID и запускаем в screen с логом
echo $$ > main.pid
python3 main.py | tee main_logs/$i.log