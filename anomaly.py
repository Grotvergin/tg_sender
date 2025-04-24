import source
from common import Stamp, ParseAccountRow, BuildService, GetSector
from event_handler import GetReactionsList, DistributeReactionsIntoEmojis, NeedToDecrease
from file import LoadRequestsFromFile, SaveRequestsToFile
from secret import MY_TG_ID, ANOMALY_SHEET_NAME, SHEET_ID, AR_TG_ID, SHEET_NAME
from source import (MONITOR_INTERVAL_MINS, POSTS_TO_CHECK, EMERGENCY_FILE,
                    BOT, LONG_SLEEP, NO_REQUIREMENTS_MESSAGE, TIME_FORMAT,
                    LINK_DECREASE_RATIO, MIN_DIFF_REAC_NORMAL, TIME_FRACTION,
                    MAX_DIFF_REAC_NORMAL, MIN_DIFF_REAC_DECREASED, MAX_DIFF_REAC_DECREASED)
# ---
from asyncio import sleep as async_sleep, run
from os.path import join
from os import getcwd
from datetime import datetime, timezone, timedelta
from random import randint
# ---
from telethon import TelegramClient


async def analyze_metric(name: str, req_dict: dict, channel_name: str, message, current_value: int) -> tuple[str, str | None]:
    """
    Возвращает: (строка для логов, строка для аномалии или None)
    """
    if channel_name not in req_dict:
        return NO_REQUIREMENTS_MESSAGE, None

    req = req_dict[channel_name]
    target = req.get('annual', 0)
    spread = req.get('spread', 0)
    time_limit_sec = req.get('time_limit', 0) * 60
    age_seconds = (datetime.now(timezone.utc) - message.date).total_seconds()
    diff_reac_num = randint(MIN_DIFF_REAC_NORMAL, MAX_DIFF_REAC_NORMAL)
    dynamic_time_limit = round(time_limit_sec * TIME_FRACTION)

    if age_seconds < dynamic_time_limit:
        return f"Пост слишком свежий (< {dynamic_time_limit // 60} мин)", None

    cur_time_coef = min(1, age_seconds / time_limit_sec)

    if NeedToDecrease(message.text, channel_name):
        if name in ('Репосты', 'Реакции'):
            target = int(float(target) / LINK_DECREASE_RATIO)
            Stamp(f'DECREASING! Now annual = {target}', 'w')
        if name == 'Реакции':
            diff_reac_num = randint(MIN_DIFF_REAC_DECREASED, MAX_DIFF_REAC_DECREASED)

    dynamic_target = round(target * cur_time_coef)
    dynamic_min_required = int((1 - spread / 100) * dynamic_target)
    dynamic_max_required = int((1 + spread / 100) * dynamic_target)
    dynamic_rand_amount = randint(dynamic_min_required, dynamic_max_required)
    info = f"{current_value}/{dynamic_target} (граница: {dynamic_min_required} при коэффициенте {cur_time_coef}})"

    if current_value < dynamic_min_required:
        lack = round((dynamic_rand_amount - current_value) / cur_time_coef)
        await create_emergency_request(name, channel_name, message.id, MY_TG_ID, lack, diff_reac_num)
        return info, f"{name} ниже минимального порога: {info}"
    return info, None


async def create_emergency_request(order_type, channel_username, message_id, initiator_id, lack_amount, diff_reac_num=None):
    now = datetime.now()
    finish = now + timedelta(minutes=MONITOR_INTERVAL_MINS)

    try:
        existing = LoadRequestsFromFile("emergency", EMERGENCY_FILE)
    except Exception:
        existing = []

    if order_type == 'Реакции':
        reac_list, reac_limit = await GetReactionsList(channel_username, randint(0, len(source.ACCOUNTS) - 1))
        if not reac_list:
            Stamp(f'No reactions for {channel_username} available', 'w')
            return
        reaction_distribution = DistributeReactionsIntoEmojis(min(diff_reac_num, reac_limit), lack_amount, reac_list)
        for emoji, count in reaction_distribution.items():
            req = {
                'order_type': order_type,
                'initiator': f"Emergency – {initiator_id}",
                'link': f"{channel_username}/{message_id}",
                'start': now.strftime(TIME_FORMAT),
                'finish': finish.strftime(TIME_FORMAT),
                'planned': count,
                'cur_acc_index': randint(0, source.ACCOUNTS_LEN - 1),
                'emoji': emoji
            }
            existing.append(req)
    else:
        req = {
            "order_type": order_type,
            "initiator": f"Emergency – {initiator_id}",
            "link": f"{channel_username}/{message_id}",
            "planned": lack_amount,
            "start": now.strftime(TIME_FORMAT),
            "finish": finish.strftime(TIME_FORMAT),
            "cur_acc_index": randint(0, source.ACCOUNTS_LEN - 1)
        }
        existing.append(req)
    SaveRequestsToFile(existing, "emergency", EMERGENCY_FILE)


async def CheckChannelPostsForAnomalies(channel_username: str, client):
    Stamp(f"Проверка канала @{channel_username}", 'i')

    try:
        entity = await client.get_entity(channel_username)
        async for message in client.iter_messages(entity, limit=POSTS_TO_CHECK):
            if not message.date or not message or not message.text:
                continue

            log_lines = []
            anomalies = []
            msg_lines = [f"Пост: https://t.me/{channel_username}/{message.id}"]
            age_seconds = (datetime.now(timezone.utc) - message.date).total_seconds()
            log_lines.append(f"Пост https://t.me/{channel_username}/{message.id}")
            log_lines.append(f"Возраст поста: {age_seconds:.0f} секунд")

            # --- Просмотры ---
            current_views = message.views or 0
            views_info, views_anomaly = await analyze_metric("Просмотры", source.AUTO_VIEWS_DICT, channel_username, message, current_views)
            log_lines.append(f"Просмотры: {views_info}")
            if views_anomaly:
                anomalies.append(views_anomaly)
                msg_lines.append(f"Просмотры: {views_info}")

            # --- Репосты ---
            current_reposts = message.forwards or 0
            reps_info, reps_anomaly = await analyze_metric("Репосты", source.AUTO_REPS_DICT, channel_username, message, current_reposts)
            log_lines.append(f"Репосты: {reps_info}")
            if reps_anomaly:
                anomalies.append(reps_anomaly)
                msg_lines.append(f"Репосты: {reps_info}")

            # --- Реакции ---
            current_reactions = sum(r.count for r in message.reactions.results) if message.reactions else 0
            reac_info, reac_anomaly = await analyze_metric("Реакции", source.AUTO_REAC_DICT, channel_username, message, current_reactions)
            log_lines.append(f"Реакции: {reac_info}")
            if reac_anomaly:
                anomalies.append(reac_anomaly)
                msg_lines.append(f"Реакции: {reac_info}")

            # --- Обработка результата ---
            if anomalies:
                Stamp("Обнаружены аномалии", 'w')
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


async def AuthorizeAccounts():
    srv = BuildService()
    row = len(GetSector('C2', 'C500', srv, ANOMALY_SHEET_NAME, SHEET_ID)) + 1
    data = GetSector('A2', f'H{row}', srv, ANOMALY_SHEET_NAME, SHEET_ID)
    accounts_len = len(GetSector('C2', 'C500', srv, SHEET_NAME, SHEET_ID))
    source.ACCOUNTS_LEN = accounts_len

    for index, account in enumerate(data):
        try:
            api_id, api_hash, num, password_tg, ip, port, login, password_proxy = ParseAccountRow(account)
        except IndexError:
            Stamp(f'Invalid account data: {account}', 'e')
            continue
        session = join(getcwd(), 'sessions', f'{num}')
        client = TelegramClient(session, api_id, api_hash, proxy=(2, ip, port, True, login, password_proxy))
        await client.start(phone=num, password=password_tg)
        source.ACCOUNTS.append(client)
        Stamp(f'Account {num} authorized', 's')


async def MonitorPostAnomalies():
    if not source.ACCOUNTS:
        Stamp("No accounts authorized, exiting anomaly monitor.", 'e')
        return

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
                if not source.ACCOUNTS:
                    Stamp(f"No accounts available to check anomalies for {channel}", 'w')
                    continue
                await CheckChannelPostsForAnomalies(channel, source.ACCOUNTS[randint(0, len(source.ACCOUNTS) - 1)])
            except Exception as e:
                Stamp(f"Error checking anomalies for {channel}: {e}", 'w')

        await async_sleep(MONITOR_INTERVAL_MINS * 60)


async def main():
    await AuthorizeAccounts()
    await MonitorPostAnomalies()


if __name__ == '__main__':
    run(main())
