from telebot.types import Message
from source import BOT
from os.path import split
from common import Sleep
import source


def SendTariffInfo(data: dict) -> (str, list):
    # TODO Fix this output
    msg = '📊 Доступные страны:\n\n'
    countries = []
    for code, info in data['countries'].items():
        msg += f'{info['name']} | {info['code']} | {'доступна' if info['enable'] else 'недоступна'}\n'
        if info['enable']:
            countries.append(info['code'])
    return msg, countries


def SendRequests(message: Message, reqs: list, amount: int = None) -> None:
    if reqs:
        reqs = reqs[-amount:] if amount else reqs
        for req in reqs:
            BOT.send_message(message.from_user.id, PrintRequest(req), parse_mode='HTML')
            Sleep(1)
    else:
        BOT.send_message(message.from_user.id, '🔍 Нет заявок')


def PrintRequest(req: dict) -> str:
    return (f"<b>Начало</b>: {req['start']}\n"
            f"<b>Конец</b>: {req['finish']}\n"
            f"<b>Тип</b>: {req['order_type']}\n"
            f"<b>Желаемое</b>: {req['planned']}\n"
            f"<b>Выполненное</b>: {req.get('current', 0)}\n"
            f"<b>Ссылка</b>: {req['link']}\n"
            f"<b>Инициатор</b>: {req['initiator']}\n"
            f"<b>Индекс аккаунта</b>: {req.get('cur_acc_index', 'N/A')}\n"
            f"<b>Эмодзи</b>: {req.get('emoji', 'N/A')}")


def PrintAutomaticRequest(chan: str, data: dict) -> str:
    return (f"<b>Канал</b>: {chan}\n"
            f"<b>Инициатор</b>: {data[chan]['initiator']}\n"
            f"<b>Временной интервал</b>: {data[chan]['time_limit']}\n"
            f"<b>Создана</b>: {data[chan]['approved']}\n"
            f"<b>На публикацию</b>: {data[chan]['annual']}\n"
            f"<b>Разброс</b>: {data[chan]['spread']}%\n"
            f"<b>Эмодзи</b>: {data[chan].get('emoji', 'N/A')}")


def ListAccountNumbers() -> str:
    res = ''
    for i, acc in enumerate(source.ACCOUNTS):
        res += f'{i + 1} | {split(acc.session.filename)[-1][:-8]}\n'
    return res
