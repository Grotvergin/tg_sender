from source import *


def Main() -> None:
    AuthorizeAccounts()
    Thread(target=BotPolling, daemon=True).start()
    loop = asyncio.get_event_loop()
    loop.create_task(ProcessRequests())
    try:
        loop.run_forever()
    finally:
        loop.close()


def BotPolling():
    while True:
        try:
            BOT.polling(none_stop=True, interval=1)
        except Exception as e:
            Stamp(f'{e}', 'e')
            Stamp(traceback.format_exc(), 'e')


def AuthorizeAccounts():
    Stamp('Authorization procedure started', 'b')
    data = GetSector('A2', 'D500', service, 'Авторизованные', SHEET_ID)
    for account in data:
        session = os.path.join(os.getcwd(), 'sessions', f'session_{account[0]}')
        client = TelegramClient(session, account[1], account[2])
        Stamp(f'Account {account[0]}', 'i')
        try:
            password = account[3] if account[3] != '-' else None
        except IndexError:
            password = None
        client.start(phone=account[0], password=password)
        ACCOUNTS.append(client)
    Stamp('All accounts authorized', 'b')


async def PerformSubscription(link: str, amount: int, channel_type: str) -> int:
    Stamp('Subscription procedure started', 'b')
    cnt_success_subs = 0
    global CUR_ACC_INDEX
    for _ in range(amount):
        acc = ACCOUNTS[CUR_ACC_INDEX]
        try:
            if channel_type == 'public':
                channel = await acc.get_entity(link)
                await acc(JoinChannelRequest(channel))
            else:
                await acc(ImportChatInviteRequest(link))
            Stamp(f"Subscribed {acc.session.filename.split('_')[-1]} to {link}", 's')
            cnt_success_subs += 1
        except Exception as e:
            Stamp(f"Failed to subscribe {acc.session.filename.split('_')[-1]} to {link}: {e}", 'e')
        CUR_ACC_INDEX = (CUR_ACC_INDEX + 1) % len(ACCOUNTS)
        Sleep(SHORT_SLEEP, 0.5)
    Stamp('Subscription procedure finished', 'b')
    return cnt_success_subs


async def ProcessRequests() -> None:
    while True:
        Stamp('Pending requests', 'i')
        for req in REQS_QUEUE:
            if datetime.now() < req['finish']:
                if req['order_type'] == 'Подписка':
                    duration = (req['finish'] - req['start']).total_seconds()
                    interval = duration / req['planned']
                    elapsed = (datetime.now() - req['start']).total_seconds()
                    expected_subs = int(elapsed / interval)
                    current_subs = req.get('current_subs', 0)
                    subs_to_add = expected_subs - current_subs
                    if subs_to_add > 0:
                        cnt_success_subs = await PerformSubscription(req['link'], subs_to_add, req['channel_type'])
                        req['current_subs'] = current_subs + cnt_success_subs
            else:
                if req['current_subs'] < req['planned']:
                    subs_to_add = req['planned'] - req['current_subs']
                    cnt_success_subs = await PerformSubscription(req['link'], subs_to_add, req['channel_type'])
                    req['current_subs'] += cnt_success_subs
                else:
                    REQS_QUEUE.remove(req)
                    BOT.send_message(req['initiator'].split(' ')[0], f"✅ Заявка выполнена:")
                    BOT.send_message(req['initiator'].split(' ')[0], PrintRequest(req), parse_mode='Markdown')
        Sleep(LONG_SLEEP)


def ChannelSub(message: telebot.types.Message) -> None:
    Stamp('Link inserting procedure', 'i')
    expected_format = r'https://t\.me/'
    if not re.match(expected_format, message.text):
        BOT.send_message(message.chat.id, "❌ Ссылка на канал не похожа на корректную. "
                                          "Пожалуйста, проверьте формат ссылки (https://t.me/channel_name_or_hash)")
        BOT.register_next_step_handler(message, ChannelSub)
    else:
        global CUR_REQ
        cut_link = message.text.split('/')[-1]
        CUR_REQ = {'order_type': 'Подписка', 'initiator': f'{message.from_user.id} ({message.from_user.username})'}
        if cut_link[0] == '+':
            CUR_REQ['link'] = cut_link[1:]
            CUR_REQ['channel_type'] = 'private'
        else:
            CUR_REQ['link'] = cut_link
            CUR_REQ['channel_type'] = 'public'
        BOT.send_message(message.from_user.id, f'❔ Введите желаемое количество подписок'
                                               f'(доступно *{len(ACCOUNTS)}* аккаунтов):', parse_mode='Markdown')
        BOT.register_next_step_handler(message, SubscribersNumber)


def SubscribersNumber(message: telebot.types.Message) -> None:
    Stamp('Number inserting procedure', 'i')
    try:
        if 0 < int(message.text) <= len(ACCOUNTS):
            CUR_REQ['planned'] = int(message.text)
            BOT.send_message(message.from_user.id, "❔ Введите промежуток времени (в минутах), "
                                                   f"в течение которого будут происходить подписки:")
            BOT.register_next_step_handler(message, SubscriptionPeriod)
        else:
            BOT.send_message(message.chat.id, "❌ Введено некорректное число. Попробуйте ещё раз:")
            BOT.register_next_step_handler(message, SubscribersNumber)
    except ValueError:
        BOT.send_message(message.chat.id, "❌ Пожалуйста, введите только число. Попробуйте ещё раз:")
        BOT.register_next_step_handler(message, SubscribersNumber)


def SubscriptionPeriod(message: telebot.types.Message) -> None:
    Stamp('Time inserting procedure', 'i')
    try:
        minutes = int(message.text)
        CUR_REQ['start'] = datetime.now()
        CUR_REQ['finish'] = datetime.now() + timedelta(minutes=minutes)
        REQS_QUEUE.append(CUR_REQ)
        BOT.send_message(message.from_user.id, "✅ Заявка принята. Начинаю выполнение подписок...")
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    except ValueError:
        BOT.send_message(message.chat.id, "❌ Пожалуйста, введите только число. Попробуйте ещё раз:")
        BOT.register_next_step_handler(message, SubscriptionPeriod)


def SendActiveRequests(message: telebot.types.Message) -> None:
    if REQS_QUEUE:
        BOT.send_message(message.from_user.id, f' ⚒ Показываю {len(REQS_QUEUE)} активные заявки:')
        for req in REQS_QUEUE:
            BOT.send_message(message.from_user.id, PrintRequest(req), parse_mode='Markdown')
        else:
            BOT.send_message(message.from_user.id, '🔍 Нет активных заявок')


def PrintRequest(req: dict) -> str:
    return f"*Начало*: {req['start'].strftime('%Y-%m-%d %H:%M')}\n" \
           f"*Конец*: {req['finish'].strftime('%Y-%m-%d %H:%M')}\n" \
           f"*Тип заявки*: {req['order_type']}\n" \
           f"*Желаемое количество*: {req['planned']}\n" \
           f"*Выполненное количество*: {req.get('current_subs', 0)}\n" \
           f"*Ссылка*: {req['link']}\n" \
           f"*Тип канала*: {req['channel_type']}\n" \
           f"*Инициатор заявки*: {req['initiator']}"


@BOT.message_handler(content_types=['text'])
def MessageAccept(message: telebot.types.Message) -> None:
    Stamp(f'User {message.from_user.id} requested {message.text}', 'i')
    if message.text == '/start':
        BOT.send_message(message.from_user.id, f'Привет, {message.from_user.first_name}!')
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    elif message.text == WELCOME_BTNS[0]:
        BOT.send_message(message.from_user.id, '❔ Введите ссылку на канал (например, https://t.me/channel_name):')
        BOT.register_next_step_handler(message, ChannelSub)
    elif message.text == WELCOME_BTNS[1]:
        BOT.send_message(message.from_user.id, '❔ Отправьте пост, на котором необходимо увеличить просмотры:')
    elif message.text == WELCOME_BTNS[2]:
        SendActiveRequests(message)
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    else:
        BOT.send_message(message.from_user.id, '❌ Я вас не понял...')
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')


if __name__ == '__main__':
    Main()
