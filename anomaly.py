from telethon import TelegramClient
import source
from common import Stamp, ParseAccountRow, BuildService, GetSector
from asyncio import sleep as async_sleep, run
from os.path import join
from os import getcwd
from file import LoadRequestsFromFile
from secret import MY_TG_ID, ANOMALY_SHEET_NAME, SHEET_ID, AR_TG_ID
from source import (MONITOR_INTERVAL, POSTS_TO_CHECK,
                    BOT, LONG_SLEEP, NO_REQUIREMENTS_MESSAGE)
from datetime import datetime, timezone


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

        await async_sleep(MONITOR_INTERVAL)


async def CheckChannelPostsForAnomalies(channel_username: str, client):
    Stamp(f"Проверка канала @{channel_username}", 'i')

    try:
        entity = await client.get_entity(channel_username)
        async for message in client.iter_messages(entity, limit=POSTS_TO_CHECK):
            if not message.date:
                continue

            age_seconds = (datetime.now(timezone.utc) - message.date).total_seconds()
            log_lines = []
            anomalies = []

            log_lines.append(f"Пост https://t.me/{channel_username}/{message.id}")
            log_lines.append(f"Возраст поста: {age_seconds:.0f} секунд")

            # --- Просмотры ---
            views_info = NO_REQUIREMENTS_MESSAGE
            if channel_username in source.AUTO_VIEWS_DICT:
                req = source.AUTO_VIEWS_DICT[channel_username]
                target_views = req.get('annual', 0)
                spread = req.get('spread', 0)
                time_limit_sec = req.get('time_limit', 0) * 60
                if age_seconds >= time_limit_sec:
                    current_views = message.views or 0
                    min_views = int((1 - spread / 100) * target_views)
                    views_info = f"{current_views}/{target_views} (граница: {min_views})"
                    if current_views < min_views:
                        anomalies.append(f"Просмотры ниже минимального порога: {views_info}")
                else:
                    views_info = f"Пост слишком свежий (< {time_limit_sec//60} мин)"
            log_lines.append(f"Просмотры: {views_info}")

            # --- Репосты ---
            reposts_info = NO_REQUIREMENTS_MESSAGE
            if channel_username in source.AUTO_REPS_DICT:
                req = source.AUTO_REPS_DICT[channel_username]
                target_reposts = req.get('annual', 0)
                spread = req.get('spread', 0)
                time_limit_sec = req.get('time_limit', 0) * 60
                if age_seconds >= time_limit_sec:
                    current_reposts = message.forwards or 0
                    min_reposts = int((1 - spread / 100) * target_reposts)
                    reposts_info = f"{current_reposts}/{target_reposts} (граница: {min_reposts})"
                    if current_reposts < min_reposts:
                        anomalies.append(f"Репосты ниже минимального порога: {reposts_info}")
                else:
                    reposts_info = f"Пост слишком свежий (< {time_limit_sec//60} мин)"
            log_lines.append(f"Репосты: {reposts_info}")

            # --- Реакции ---
            reactions_info = NO_REQUIREMENTS_MESSAGE
            if channel_username in source.AUTO_REAC_DICT:
                req = source.AUTO_REAC_DICT[channel_username]
                target_reactions = req.get('annual', 0)
                spread = req.get('spread', 0)
                time_limit_sec = req.get('time_limit', 0) * 60
                if age_seconds >= time_limit_sec:
                    current_reactions = sum(r.count for r in message.reactions.results) if message.reactions else 0
                    min_reactions = int((1 - spread / 100) * target_reactions)
                    reactions_info = f"{current_reactions}/{target_reactions} (граница: {min_reactions})"
                    if current_reactions < min_reactions:
                        anomalies.append(f"Реакции ниже минимального порога: {reactions_info}")
                else:
                    reactions_info = f"Пост слишком свежий (< {time_limit_sec//60} мин)"
            log_lines.append(f"Реакции: {reactions_info}")

            if anomalies:
                Stamp("Обнаружны аномалии", 'w')
                for line in log_lines:
                    Stamp(line, 'i')
                for anomaly in anomalies:
                    Stamp(f"Аномалия: {anomaly}", 'w')

                msg_lines = [f"Пост: https://t.me/{channel_username}/{message.id}"]

                # Включаем в сообщение только строки, связанные с конкретными аномалиями
                for anomaly in anomalies:
                    if "Просмотры" in anomaly:
                        msg_lines.append(f"Просмотры: {views_info}")
                    if "Репосты" in anomaly:
                        msg_lines.append(f"Репосты: {reposts_info}")
                    if "Реакции" in anomaly:
                        msg_lines.append(f"Реакции: {reactions_info}")

                msg = '\n'.join(msg_lines)
                BOT.send_message(MY_TG_ID, msg)
                BOT.send_message(AR_TG_ID, msg)
            else:
                for line in log_lines:
                    Stamp(line, 's')
                Stamp("Пост в норме", 's')

    except Exception as e:
        Stamp(f"Ошибка при обработке канала {channel_username}: {e}", 'e')

    await async_sleep(LONG_SLEEP * 4)



if __name__ == '__main__':
    run(MonitorPostAnomalies())
