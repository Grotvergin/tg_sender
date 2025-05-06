#!/bin/bash

cd ~/tg_sender/
mkdir -p anomaly_logs
source ./venv/bin/activate

# Найдём номер следующего лога
i=0
while [[ -f "anomaly_logs/$i.log" ]]; do
  ((i++))
done

# Сохраняем PID и запускаем в screen с логом
echo $$ > anomaly.pid
python anomaly.py | tee anomaly_logs/$i.log