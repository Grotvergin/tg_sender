import source
from adders import PerformSubscription, IncreasePostViews, RepostMessage, AddReactions
from common import Stamp, AsyncSleep
from source import (BOT, TIME_FORMAT, MAX_MINS_REQ, LONG_SLEEP, NOTIF_TIME_DELTA,
                    FILE_ACTIVE, SHORT_SLEEP, EMERGENCY_FILE, LAST_MAIN_CHECK_FILE)
from datetime import datetime, timedelta
from file import SaveRequestsToFile, LoadRequestsFromFile, updateDailyStats
from info_senders import PrintRequest
from secret import MY_TG_ID, AR_TG_ID
from monitor import update_last_check
from event_handler import GetSubscribedChannels
from asyncio import sleep as async_sleep, gather
from collections import Counter
# ---
from telethon.errors import (ReactionInvalidError, MessageIdInvalidError,
                             ChannelPrivateError, ChatIdInvalidError,
                             PeerIdInvalidError, ChannelInvalidError,
                             InviteHashInvalidError)


async def CancelRequest(req: dict, reason: str):
    Stamp(f'{reason} in {req["link"]}, removing req', 'w')
    BOT.send_message(req['initiator'].split(' ')[-1], f'⛔️ {reason} {req["link"]}, заявка снимается...')
    source.REQS_QUEUE.remove(req)
    SaveRequestsToFile(source.REQS_QUEUE, 'active', FILE_ACTIVE)


async def ProcessOrder(req: dict, to_add: int):
    if req['order_type'] == 'Подписка':
        try:
            cnt_success = await PerformSubscription(req['link'], to_add, req['channel_type'], req['cur_acc_index'])
        except ChannelInvalidError:
            await CancelRequest(req, 'Некорректная ссылка на канал')
            return
        except InviteHashInvalidError:
            await CancelRequest(req, 'Некорректная ссылка на канал')
            return
    elif req['order_type'] == 'Просмотры':
        try:
            cnt_success = await IncreasePostViews(req['link'], to_add, req['cur_acc_index'])
        except ChannelPrivateError:
            await CancelRequest(req, 'Ссылка ведёт на приватный канал')
            return
        except (ChatIdInvalidError, PeerIdInvalidError):
            await CancelRequest(req, 'Некорректная ссылка на пост')
            return
    elif req['order_type'] == 'Репосты':
        try:
            cnt_success = await RepostMessage(req['link'], to_add, req['cur_acc_index'])
        except MessageIdInvalidError:
            await CancelRequest(req, 'Некорректная ссылка на пост')
            return
    elif req['order_type'] == 'Реакции':
        try:
            cnt_success = await AddReactions(req['link'], to_add, req['cur_acc_index'], req['emoji'])
        except ReactionInvalidError as e:
            Stamp(f"Bad reaction {req['emoji']} for {req['link']}: {e}", 'e')
            BOT.send_message(req['initiator'].split(' ')[-1], f"⚠️ Запрошенная реакция {req['emoji']} недоступна для заявки {req['link']}, заявка снимается...")
            await CancelRequest(req, f"Запрошенная реакция {req['emoji']} недоступна для заявки")
            return
        except KeyError as e:
            Stamp(f'No emoji key for {req['link']}: {e}', 'e')
            BOT.send_message(req['initiator'].split(' ')[-1], f'💊 Не указана реакция для заявки {req['link']}, заявка снимается...')
            await CancelRequest(req, f"Не указана реакция для заявки {req['link']}")
            return
    else:
        Stamp('Unknown order type', 'e')
        return
    if len(source.ACCOUNTS) == 0:
        Stamp('No available accounts', 'e')
        return
    req['cur_acc_index'] = (req['cur_acc_index'] + to_add) % len(source.ACCOUNTS)
    req['current'] = req.get('current', 0) + cnt_success


def sendNotificationAboutWork():
    if datetime.now() - source.LAST_NOTIF_PROCESSOR > timedelta(minutes=NOTIF_TIME_DELTA):
        type_counts = Counter(req.get("order_type", "Неизвестно") for req in source.REQS_QUEUE)
        total_unique_auto = len(set(source.AUTO_VIEWS_DICT.keys()) | set(source.AUTO_REPS_DICT.keys()) | set(source.AUTO_REAC_DICT.keys()))
        auto_count = 0
        emergency_count = 0
        unknown_count = 0

        for req in source.REQS_QUEUE:
            initiator = req.get("initiator", "")
            if initiator.startswith("Emergency"):
                emergency_count += 1
            elif initiator.startswith("Автоматическая"):
                auto_count += 1
            else:
                unknown_count += 1

        msg = (
            f'1️⃣ <b>В очереди ({len(source.REQS_QUEUE)})</b>\n'
            f'💡 Автоматических: {auto_count}\n'
            f'⚠️ Аномальных: {emergency_count}\n'
            f'❕ Исключительных: {unknown_count}\n'
            f'👀 Просмотры: {type_counts['Просмотры']}\n'
            f'📢 Репосты: {type_counts['Репосты']}\n'
            f'❤️ Реакции: {type_counts['Реакции']}\n\n'
            
            f'📅 <b>За текущие сутки</b>\n'
            f'✅ Выполнено: {source.DAILY_STATS["finished"]}\n'
            f'🛑 Снято: {source.DAILY_STATS["expired"]}\n\n'

            f'⌛️ <b>Автоматические ({total_unique_auto} уникальных)</b>\n'
            f'👀 Просмотры: {len(source.AUTO_VIEWS_DICT)}\n'
            f'📢 Репосты: {len(source.AUTO_REPS_DICT)}\n'
            f'❤️ Реакции: {len(source.AUTO_REAC_DICT)}'
        )

        BOT.send_message(MY_TG_ID, msg, parse_mode='HTML')
        BOT.send_message(AR_TG_ID, msg, parse_mode='HTML')

        update_last_check(LAST_MAIN_CHECK_FILE)
        source.LAST_NOTIF_PROCESSOR = datetime.now()


async def ProcessRequest(req: dict, i: int):
    async with source.SEMAPHORE:
        try:
            finish = datetime.strptime(req['finish'], TIME_FORMAT)
            start = datetime.strptime(req['start'], TIME_FORMAT)
            now = datetime.now()
            if now < finish:
                duration = (finish - start).total_seconds()
                interval = duration / req['planned']
                elapsed = (now - start).total_seconds()
                expected = int(elapsed / interval)
                current = req.get('current', 0)
                to_add = expected - current
                if to_add > 0:
                    await ProcessOrder(req, to_add)
            else:
                if now < finish + timedelta(minutes=MAX_MINS_REQ) and req.get('current', 0) < req['planned']:
                    to_add = req['planned'] - req.get('current', 0)
                    await ProcessOrder(req, to_add)
                else:
                    if req.get('current', 0) < req['planned']:
                        message = f"⚠️ Заявка снята из-за истечения времени\n\n{PrintRequest(req)}"
                        updateDailyStats('expired')
                    else:
                        message = f"✅ Заявка выполнена\n\n{PrintRequest(req)}"
                        updateDailyStats('finished')
                    source.REQS_QUEUE.remove(req)
                    source.FINISHED_REQS.append(req)
                    user_id = req['initiator'].split(' ')[-1]
                    BOT.send_message(user_id, message, parse_mode='HTML')
        except Exception as e:
            Stamp(f'Error processing request #{i}: {e}', 'w')
            BOT.send_message(MY_TG_ID, f'🔴 Ошибка в обработке заявки #{i}')


async def ProcessRequests() -> None:
    while True:
        try:
            Stamp('Pending requests', 'i')
            emergency = LoadRequestsFromFile("emergency", EMERGENCY_FILE)
            if emergency:
                Stamp(f"Loaded {len(emergency)} emergency requests", 'i')
                source.REQS_QUEUE.extend(emergency)
                SaveRequestsToFile(source.REQS_QUEUE, 'active', FILE_ACTIVE)
                SaveRequestsToFile([], "emergency", EMERGENCY_FILE)
            sendNotificationAboutWork()

            tasks = []
            for i, req in enumerate(source.REQS_QUEUE):
                tasks.append(ProcessRequest(req, i))

            await gather(*tasks)
            SaveRequestsToFile(source.REQS_QUEUE, 'active', FILE_ACTIVE)
            SaveRequestsToFile(source.FINISHED_REQS, 'finished', 'finished.json')

        except Exception as e:
            Stamp(f'Uncaught exception in processor happened: {e}', 'w')
            BOT.send_message(MY_TG_ID, '🔴 Ошибка в ProcessRequests')

        await AsyncSleep(LONG_SLEEP, 0.5)


async def loopCheckSubscriptions() -> None:
    while True:
        if source.CHECK_CHANNEL_LINK:
            Stamp('CHECK_CHANNEL_LINK is set, checking a channel', 'i')
            link = source.CHECK_CHANNEL_LINK
            if link.startswith('@'):
                link = link[1:]
            elif 't.me/' in link:
                link = link.split('t.me/')[-1].strip('/')
            else:
                BOT.send_message(source.CHECK_CHANNEL_USER, "❌ Неверная ссылка. Используйте формат @name или https://t.me/name")
                source.CHECK_CHANNEL_USER = None
                source.CHECK_CHANNEL_LINK = None
                continue
            available_accounts = await checkSubscriptions(link)
            if source.CHECK_CHANNEL_USER:
                BOT.send_message(source.CHECK_CHANNEL_USER, f'⚒️ Доступно для подписки {available_accounts} аккаунтов')
            source.CHECK_CHANNEL_USER = None
            source.CHECK_CHANNEL_LINK = None
        await async_sleep(SHORT_SLEEP)


def acceptCheckSubscriptions(message):
    source.CHECK_CHANNEL_USER = message.from_user.id
    source.CHECK_CHANNEL_LINK = message.text.strip()


async def checkSubscriptions(link):
    total_accounts = len(source.ACCOUNTS)
    already_subscribed = 0

    for acc in source.ACCOUNTS:
        try:
            subscribed_channels = await GetSubscribedChannels(acc)
            if link.lower() in (ch.lower() for ch in subscribed_channels):
                already_subscribed += 1
        except Exception as e:
            Stamp(f"Error checking subscriptions for account: {e}", 'w')
            continue

    available_accounts = total_accounts - already_subscribed
    source.CHECKED_AVAILABLE_COUNT = available_accounts
    return available_accounts
