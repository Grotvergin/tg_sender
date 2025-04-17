from telethon import TelegramClient
import source
from common import Stamp, ParseAccountRow, BuildService, GetSector
from asyncio import sleep as async_sleep, run
from os.path import join
from os import getcwd
from file import LoadRequestsFromFile, SaveRequestsToFile
from secret import MY_TG_ID, ANOMALY_SHEET_NAME, SHEET_ID, AR_TG_ID
from source import (MONITOR_INTERVAL_MINS, POSTS_TO_CHECK, EMERGENCY_FILE,
                    BOT, LONG_SLEEP, NO_REQUIREMENTS_MESSAGE, UPPER_COEF)
from datetime import datetime, timezone, timedelta
from random import randint


async def MonitorPostAnomalies():
    srv = BuildService()
    data = GetSector('A2', f'H2', srv, ANOMALY_SHEET_NAME, SHEET_ID)
    api_id, api_hash, num, password_tg, ip, port, login, password_proxy = ParseAccountRow(data[0])
    session = join(getcwd(), 'sessions', f'{num}')
    client = TelegramClient(session, api_id, api_hash, proxy=(2, ip, port, True, login, password_proxy))
    await client.start(phone=num, password=password_tg)

    while True:
        source.AUTO_VIEWS_DICT = LoadRequestsFromFile('automatic views', source.FILE_AUTO_VIEWS)
        source.AUTO_REPS_DICT = LoadRequestsFromFile('automatic reposts', source.FILE_AUTO_REPS)
        source.AUTO_REAC_DICT = LoadRequestsFromFile('automatic reactions', source.FILE_AUTO_REAC)
        channels = list(set(
            list(source.AUTO_VIEWS_DICT.keys()) +
            list(source.AUTO_REPS_DICT.keys()) +
            list(source.AUTO_REAC_DICT.keys())
        ))

        for channel in channels:
            try:
                await CheckChannelPostsForAnomalies(channel, client)
            except Exception as e:
                Stamp(f"Error checking anomalies for {channel}: {e}", 'w')

        await async_sleep(MONITOR_INTERVAL_MINS * 60)


def analyze_metric(name: str, req_dict: dict, channel_username: str, message, current_value: int) -> tuple[str, str | None]:
    """
    Возвращает: (строка для логов, строка для аномалии или None)
    """
    if channel_username not in req_dict:
        return NO_REQUIREMENTS_MESSAGE, None

    req = req_dict[channel_username]
    target = req.get('annual', 0)
    spread = req.get('spread', 0)
    time_limit_sec = req.get('time_limit', 0) * 60
    age_seconds = (datetime.now(timezone.utc) - message.date).total_seconds()

    if age_seconds < time_limit_sec:
        return f"Пост слишком свежий (< {time_limit_sec // 60} мин)", None

    min_required = int((1 - spread / 100) * target)
    info = f"{current_value}/{target} (граница: {min_required})"

    if current_value < min_required:
        lack = min_required - current_value
        create_emergency_request(name, channel_username, message.id, MY_TG_ID, lack)
        return info, f"{name} ниже минимального порога: {info}"
    return info, None


def create_emergency_request(order_type, channel_username, message_id, initiator_id, lack_amount):
    now = datetime.now()
    finish = now + timedelta(minutes=MONITOR_INTERVAL_MINS)
    req = {
        "order_type": order_type,
        "initiator": f"Emergency – {initiator_id}",
        "link": f"{channel_username}/{message_id}",
        "planned": int(round(lack_amount * UPPER_COEF)),
        "start": now.strftime("%Y-%m-%d %H:%M"),
        "finish": finish.strftime("%Y-%m-%d %H:%M"),
        "cur_acc_index": randint(0, len(source.ACCOUNTS) - 1)
    }

    try:
        existing = LoadRequestsFromFile("emergency", EMERGENCY_FILE)
    except Exception:
        existing = []

    existing.append(req)
    SaveRequestsToFile(existing, "emergency", EMERGENCY_FILE)
    Stamp(f"Создана разовая заявка: {req}", 'w')


async def CheckChannelPostsForAnomalies(channel_username: str, client):
    Stamp(f"Проверка канала @{channel_username}", 'i')

    try:
        entity = await client.get_entity(channel_username)
        async for message in client.iter_messages(entity, limit=POSTS_TO_CHECK):
            if not message.date:
                continue

            log_lines = []
            anomalies = []
            msg_lines = [f"Пост: https://t.me/{channel_username}/{message.id}"]
            age_seconds = (datetime.now(timezone.utc) - message.date).total_seconds()
            log_lines.append(f"Пост https://t.me/{channel_username}/{message.id}")
            log_lines.append(f"Возраст поста: {age_seconds:.0f} секунд")

            # --- Просмотры ---
            current_views = message.views or 0
            views_info, views_anomaly = analyze_metric("Просмотры", source.AUTO_VIEWS_DICT, channel_username, message, current_views)
            log_lines.append(f"Просмотры: {views_info}")
            if views_anomaly:
                anomalies.append(views_anomaly)
                msg_lines.append(f"Просмотры: {views_info}")

            # --- Репосты ---
            current_reposts = message.forwards or 0
            reps_info, reps_anomaly = analyze_metric("Репосты", source.AUTO_REPS_DICT, channel_username, message, current_reposts)
            log_lines.append(f"Репосты: {reps_info}")
            if reps_anomaly:
                anomalies.append(reps_anomaly)
                msg_lines.append(f"Репосты: {reps_info}")

            # --- Реакции ---
            current_reactions = sum(r.count for r in message.reactions.results) if message.reactions else 0
            reac_info, reac_anomaly = analyze_metric("Реакции", source.AUTO_REAC_DICT, channel_username, message, current_reactions)
            log_lines.append(f"Реакции: {reac_info}")
            if reac_anomaly:
                anomalies.append(reac_anomaly)
                msg_lines.append(f"Реакции: {reac_info}")

            # --- Обработка результата ---
            if anomalies:
                Stamp("Обнаружны аномалии", 'w')
                for line in log_lines:
                    Stamp(line, 'i')
                for anomaly in anomalies:
                    Stamp(f"Аномалия: {anomaly}", 'w')
                msg = '\n'.join(msg_lines)
                BOT.send_message(MY_TG_ID, msg)
                BOT.send_message(AR_TG_ID, msg)
            else:
                for line in log_lines:
                    Stamp(line, 's')
                Stamp("Пост в норме", 's')

    except Exception as e:
        Stamp(f"Ошибка при обработке канала {channel_username}: {e}", 'e')

    await async_sleep(LONG_SLEEP * 2)


if __name__ == '__main__':
    run(MonitorPostAnomalies())
