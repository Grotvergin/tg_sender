import source
from common import Sleep
from source import BOT, REQS_PORTION, SHORT_SLEEP
# ---
from os.path import split
# ---
from telebot.types import Message


def SendTariffInfo(data: dict) -> (str, list):
    msg = '```\n'
    countries = []
    header = f"{'Страна':<21} | {'Код':<4}\n"
    msg += header
    msg += '-' * len(header) + '\n'
    for code, info in data['countries'].items():
        line = f"{info['name']:<19} | {info['code']:<4}\n"
        msg += line
        if info['enable']:
            countries.append(info['code'])
    msg += '\n```'
    return msg, countries


def SendRequests(message: Message, reqs: list, start_idx: int, end_idx: int) -> None:
    if reqs:
        cut_reqs = reqs[start_idx:end_idx]
        BOT.send_message(message.from_user.id, f"🔍 Общее количество разовых заявок: {len(reqs)}, показываю: {len(cut_reqs)}")
        for idx, i in enumerate(range(0, len(cut_reqs), REQS_PORTION)):
            portion_requests = cut_reqs[i:i + REQS_PORTION]
            msg = ''
            for j, req in enumerate(portion_requests, start=1):
                separator = '	—' * 5
                msg += f"{separator} {start_idx + idx * REQS_PORTION + j} {separator}\n"
                msg += PrintRequest(req) + '\n'
            BOT.send_message(message.from_user.id, msg, parse_mode='HTML')
            Sleep(SHORT_SLEEP)
    else:
        BOT.send_message(message.from_user.id, '🔍 Нет разовых заявок')


def SendAutomaticRequests(message: Message, data: dict, portion: int = REQS_PORTION) -> None:
    if data.keys():
        BOT.send_message(message.from_user.id, f"🔍 Общее количество автоматических заявок: {len(data)}")
        channels = list(data.keys())
        for idx, i in enumerate(range(0, len(channels), portion)):
            portion_requests = channels[i:i + portion]
            msg = ''
            for j, chan in enumerate(portion_requests, start=1):
                separator = '	—' * 5
                msg += f"{separator} {idx * portion + j} {separator}\n"
                msg += PrintAutomaticRequest(chan, data) + '\n'
            BOT.send_message(message.from_user.id, msg, parse_mode='HTML')
            Sleep(SHORT_SLEEP)
    else:
        BOT.send_message(message.from_user.id, '🔍 Нет автоматических заявок')


def PrintRequest(req: dict) -> str:
    return (f"<b>Начало</b>: {req['start']}\n"
            f"<b>Конец</b>: {req['finish']}\n"
            f"<b>Тип</b>: {req['order_type']}\n"
            f"<b>Желаемое</b>: {req['planned']}\n"
            f"<b>Выполненное</b>: {req.get('current', 0)}\n"
            f"<b>Ссылка</b>: https://t.me/{req['link']}\n"
            f"<b>Инициатор</b>: {req['initiator']}\n"
            f"<b>Эмодзи</b>: {req.get('emoji', 'N/A')}")


def PrintAutomaticRequest(chan: str, data: dict) -> str:
    return (f"<b>Канал</b>: {chan}\n"
            f"<b>Инициатор</b>: {data[chan]['initiator']}\n"
            f"<b>Временной интервал</b>: {data[chan]['time_limit']}\n"
            f"<b>Создана</b>: {data[chan]['approved']}\n"
            f"<b>На публикацию</b>: {data[chan]['annual']}\n"
            f"<b>Разброс</b>: {data[chan]['spread']}%\n")


def SendAccountNumbers(user_id):
    """
    Отправляет пользователю список доступных аккаунтов порциями по 100 штук.
    """
    total_accounts = len(source.ACCOUNTS)
    BOT.send_message(user_id, f'👁 Доступно {total_accounts} аккаунтов:')

    messages = []
    chunk = []

    for i, acc in enumerate(source.ACCOUNTS, start=1):
        chunk.append(f'{i} | {split(acc.session.filename)[-1][:-8]}')

        if len(chunk) == 100:
            messages.append("\n".join(chunk))
            chunk = []

    if chunk:
        messages.append("\n".join(chunk))

    for msg in messages:
        BOT.send_message(user_id, msg)
