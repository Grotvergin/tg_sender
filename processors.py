from adders import (PerformSubscription, IncreasePostViews,
                    RepostMessage, AddReactions)
from common import Stamp, AsyncSleep
from source import (BOT, REQS_QUEUE, TIME_FORMAT, FINISHED_REQS,
                    ACCOUNTS, MAX_MINS_REQ, LONG_SLEEP)
from datetime import datetime, timedelta
from telethon.errors import ReactionInvalidError
from file import SaveRequestsToFile
from info_senders import PrintRequest


async def ProcessOrder(req: dict, to_add: int):
    if req['order_type'] == 'Подписка':
        cnt_success = await PerformSubscription(req['link'], to_add, req['channel_type'], req['cur_acc_index'])
    elif req['order_type'] == 'Просмотры':
        cnt_success = await IncreasePostViews(req['link'], to_add, req['cur_acc_index'])
    elif req['order_type'] == 'Репосты':
        cnt_success = await RepostMessage(req['link'], to_add, req['cur_acc_index'])
    elif req['order_type'] == 'Реакции':
        try:
            cnt_success = await AddReactions(req['link'], to_add, req['cur_acc_index'], req['emoji'])
        except ReactionInvalidError as e:
            Stamp(f"Bad reaction {req['emoji']} for {req['link']}: {e}", 'e')
            BOT.send_message(req['initiator'].split(' ')[-1], f"⚠️ Запрошенная реакция {req['emoji']} недоступна для заявки {req['link']}, заявка снимается...")
            REQS_QUEUE.remove(req)
            return
    else:
        Stamp('Unknown order type', 'e')
        return
    req['cur_acc_index'] = (req['cur_acc_index'] + to_add) % len(ACCOUNTS)
    req['current'] = req.get('current', 0) + cnt_success


async def ProcessRequests() -> None:
    while True:
        Stamp('Pending requests', 'i')
        for req in REQS_QUEUE:
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
                    else:
                        message = f"✅ Заявка выполнена\n\n{PrintRequest(req)}"

                    REQS_QUEUE.remove(req)
                    FINISHED_REQS.append(req)
                    SaveRequestsToFile(FINISHED_REQS, 'finished', 'finished.json')
                    user_id = req['initiator'].split(' ')[-1]
                    BOT.send_message(user_id, message, parse_mode='HTML')
        await AsyncSleep(LONG_SLEEP, 0.5)
