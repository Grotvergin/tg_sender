import source
from common import Stamp, ParseAccountRow, BuildService, GetSector
from event_handler import GetReactionsList, DistributeReactionsIntoEmojis, NeedToDecrease
from file import LoadRequestsFromFile, SaveRequestsToFile
from monitor import update_last_check
from secret import ANOMALY_SHEET_NAME, SHEET_ID, SHEET_NAME, MANAGER_TG_ID, MY_TG_ID, AR_TG_ID
from source import (MONITOR_INTERVAL_MINS, POSTS_TO_CHECK, EMERGENCY_FILE,
                    TIME_FORMAT, LINK_DECREASE_RATIO, MIN_DIFF_REAC_NORMAL,
                    TIME_FRACTION, MAX_DIFF_REAC_NORMAL, MIN_DIFF_REAC_DECREASED,
                    MAX_DIFF_REAC_DECREASED, SHORT_SLEEP, CACHE_FILE,
                    MAX_AVG_POSTS_CHECK, POSTS_FOR_AVG, START_ANOMALY_COUNT_HOURS,
                    START_AVG_COUNT_HOURS, THRESHOLD_AVG_ANOMALY_VIEWS, BOT)
# ---
from asyncio import sleep as async_sleep, run
from os.path import join, exists
from os import getcwd
from datetime import datetime, timezone, timedelta
from random import randint
from json import load, dump
# ---
from telethon import TelegramClient


async def handleReactions(channel_name, message):
    if channel_name not in source.AUTO_REAC_DICT:
        return

    cur_value = sum(r.count for r in message.reactions.results) if message.reactions else 0
    req = source.AUTO_REAC_DICT[channel_name]
    target = req.get('annual', 0)
    spread = req.get('spread', 0)
    time_limit_sec = req.get('time_limit', 0) * 60
    age_seconds = (datetime.now(timezone.utc) - message.date).total_seconds()
    diff_reac_num = randint(MIN_DIFF_REAC_NORMAL, MAX_DIFF_REAC_NORMAL)
    dynamic_time_limit = round(time_limit_sec * TIME_FRACTION)

    if age_seconds < dynamic_time_limit:
        Stamp(f'Post is too fresh (< {dynamic_time_limit // 60} minutes)', 'i')

    if NeedToDecrease(message.text, channel_name):
        Stamp(f'DECREASING! Now annual = {target}', 'w')
        target = int(float(target) / LINK_DECREASE_RATIO)
        diff_reac_num = randint(MIN_DIFF_REAC_DECREASED, MAX_DIFF_REAC_DECREASED)

    cur_time_coef = min(1, age_seconds / time_limit_sec)
    dynamic_target = round(target * cur_time_coef)
    dynamic_min_required = int((1 - spread / 100) * dynamic_target)
    dynamic_max_required = int((1 + spread / 100) * dynamic_target)
    dynamic_rand_amount = randint(dynamic_min_required, dynamic_max_required)
    Stamp(f'Reactions {cur_value}/{dynamic_target} (border: {dynamic_min_required} with coefficient {cur_time_coef})', 'i')

    if cur_value < dynamic_min_required:
        lack = round((dynamic_rand_amount - cur_value) / cur_time_coef)
        now = datetime.now()
        finish = now + timedelta(minutes=MONITOR_INTERVAL_MINS)

        existing = LoadRequestsFromFile("emergency", EMERGENCY_FILE)
        reac_list, reac_limit = await GetReactionsList(channel_name, randint(0, len(source.ACCOUNTS) - 1))
        reaction_distribution = DistributeReactionsIntoEmojis(min(diff_reac_num, reac_limit), lack, reac_list)
        for emoji, count in reaction_distribution.items():
            req = {
                'order_type': 'Реакции',
                'initiator': f"Emergency – {MANAGER_TG_ID}",
                'link': f"{channel_name}/{message.id}",
                'start': now.strftime(TIME_FORMAT),
                'finish': finish.strftime(TIME_FORMAT),
                'planned': count,
                'cur_acc_index': randint(0, source.ACCOUNTS_LEN - 1),
                'emoji': emoji
            }
            existing.append(req)
        SaveRequestsToFile(existing, "emergency", EMERGENCY_FILE)


async def handleReposts(channel_name, message):
    if channel_name not in source.AUTO_REPS_DICT:
        return

    cur_value = message.forwards or 0
    req = source.AUTO_REPS_DICT[channel_name]
    target = req.get('annual', 0)
    spread = req.get('spread', 0)
    time_limit_sec = req.get('time_limit', 0) * 60
    age_seconds = (datetime.now(timezone.utc) - message.date).total_seconds()
    dynamic_time_limit = round(time_limit_sec * TIME_FRACTION)

    if age_seconds < dynamic_time_limit:
        Stamp(f'Post is too fresh (< {dynamic_time_limit // 60} minutes)', 'i')

    if NeedToDecrease(message.text, channel_name):
        Stamp(f'DECREASING! Now annual = {target}', 'w')
        target = int(float(target) / LINK_DECREASE_RATIO)

    cur_time_coef = min(1, age_seconds / time_limit_sec)
    dynamic_target = round(target * cur_time_coef)
    dynamic_min_required = int((1 - spread / 100) * dynamic_target)
    dynamic_max_required = int((1 + spread / 100) * dynamic_target)
    dynamic_rand_amount = randint(dynamic_min_required, dynamic_max_required)
    Stamp(f'Reposts {cur_value}/{dynamic_target} (border: {dynamic_min_required} with coefficient {cur_time_coef})', 'i')

    if cur_value < dynamic_min_required:
        lack = round((dynamic_rand_amount - cur_value) / cur_time_coef)
        now = datetime.now()
        finish = now + timedelta(minutes=MONITOR_INTERVAL_MINS)
        existing = LoadRequestsFromFile("emergency", EMERGENCY_FILE)
        req = {
            "order_type": 'Репосты',
            "initiator": f"Emergency – {MANAGER_TG_ID}",
            "link": f"{channel_name}/{message.id}",
            "planned": lack,
            "start": now.strftime(TIME_FORMAT),
            "finish": finish.strftime(TIME_FORMAT),
            "cur_acc_index": randint(0, source.ACCOUNTS_LEN - 1)
        }
        existing.append(req)
        SaveRequestsToFile(existing, "emergency", EMERGENCY_FILE)


def loadAvgViews():
    Stamp('Loading cached average views', 'i')
    if exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            source.CACHE_VIEWS = load(f)
    else:
        source.CACHE_VIEWS = {}


def saveAvgViews():
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        dump(source.CACHE_VIEWS, f, ensure_ascii=False, indent=2)


async def handleViews(channel_name, message):
    if channel_name not in source.AUTO_VIEWS_DICT:
        return

    cur_value = message.views or 0
    age_seconds = (datetime.now(timezone.utc) - message.date).total_seconds()

    if age_seconds < START_ANOMALY_COUNT_HOURS * 3600:
        return

    cache_entry = source.CACHE_VIEWS.get(channel_name, {})
    avg_views = cache_entry.get("avg_views")

    if avg_views is None:
        return

    threshold = avg_views * THRESHOLD_AVG_ANOMALY_VIEWS
    if cur_value < threshold:
        percent_below = (threshold - cur_value) / threshold * 100
        text = (
            f"🚨 https://t.me/{channel_name}/{message.id}\n"
            f"👁 Просмотров: {cur_value}\n"
            f"〽️ Среднее: {avg_views:.1f}\n"
            f"⬆️ Нижняя граница: {threshold:.1f}\n"
            f"🔺 Просмотров меньше на: {percent_below:.1f}%\n"
            f"🕔 Возраст: {round(age_seconds / 3600, 1)} часов"
        )
        BOT.send_message(MY_TG_ID, text)
        BOT.send_message(AR_TG_ID, text)
        Stamp(f"View anomaly detected (@{channel_name}/{message.id}): {cur_value} < {threshold:.1f}", 'w')


def avgViewsNeedUpdate(channel_name):
    data = source.CACHE_VIEWS.get(channel_name)
    if not data:
        return True
    try:
        last_update = datetime.fromisoformat(data.get("last_update"))
    except:
        return True
    return datetime.now(timezone.utc) - last_update > timedelta(hours=24)


async def updateAvgViews(client, channel_name, entity):
    views_list = []
    async for message in client.iter_messages(entity, limit=MAX_AVG_POSTS_CHECK):
        if not message.date or not message.views:
            continue
        age = (datetime.now(timezone.utc) - message.date).total_seconds()
        if age >= START_AVG_COUNT_HOURS * 3600:
            views_list.append(message.views)
        if len(views_list) >= POSTS_FOR_AVG:
            break
    if len(views_list) < POSTS_FOR_AVG:
        Stamp(f"Not enough posts (>24h) to update avg views for @{channel_name} ({len(views_list)})", "i")
        avg_views = None
    else:
        avg_views = sum(views_list) / len(views_list)
        Stamp(f"Updated avg views for @{channel_name}: {avg_views:.1f}", "i")
    source.CACHE_VIEWS[channel_name] = {
        "last_update": datetime.now(timezone.utc).isoformat(),
        "avg_views": avg_views
    }
    saveAvgViews()
    return avg_views


async def CheckChannelPostsForAnomalies(channel_username: str, client):
    Stamp(f"Checking channel @{channel_username}", 'i')
    try:
        entity = await client.get_entity(channel_username)

        if avgViewsNeedUpdate(channel_username):
            await updateAvgViews(client, channel_username, entity)

        async for message in client.iter_messages(entity, limit=POSTS_TO_CHECK):
            if not message.date or not message or not message.text:
                continue

            await handleViews(channel_username, message)
            await handleReposts(channel_username, message)
            await handleReactions(channel_username, message)

    except Exception as e:
        Stamp(f"Error checking channel @{channel_username}: {e}", 'e')

    await async_sleep(SHORT_SLEEP * 5)


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

    i = 0

    while True:
        update_last_check(source.LAST_ANOMALY_CHECK_FILE)
        source.AUTO_VIEWS_DICT = LoadRequestsFromFile('automatic views', source.FILE_AUTO_VIEWS)
        source.AUTO_REPS_DICT = LoadRequestsFromFile('automatic reposts', source.FILE_AUTO_REPS)
        source.AUTO_REAC_DICT = LoadRequestsFromFile('automatic reactions', source.FILE_AUTO_REAC)
        channels = list(set(
            list(source.AUTO_VIEWS_DICT.keys()) +
            list(source.AUTO_REPS_DICT.keys()) +
            list(source.AUTO_REAC_DICT.keys())
        ))

        for channel in channels:
            update_last_check(source.LAST_ANOMALY_CHECK_FILE)
            try:
                if not source.ACCOUNTS:
                    Stamp(f"No accounts available to check anomalies for {channel}", 'w')
                    continue

                account = source.ACCOUNTS[i]
                i = (i + 1) % len(source.ACCOUNTS)

                await CheckChannelPostsForAnomalies(channel, account)

            except Exception as e:
                Stamp(f"Error checking anomalies for {channel}: {e}", 'w')

        await async_sleep(MONITOR_INTERVAL_MINS)


async def main():
    await AuthorizeAccounts()
    await MonitorPostAnomalies()


if __name__ == '__main__':
    run(main())
