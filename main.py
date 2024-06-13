from source import *


def Main() -> None:
    AuthorizeAccounts()
    global FINISHED_REQS
    FINISHED_REQS = LoadFinishedRequests()
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


async def IncreasePostViews(post_link: str, views_needed: int) -> int:
    Stamp('View increasing procedure started', 'b')
    cnt_success_views = 0
    global CUR_ACC_INDEX
    for _ in range(views_needed):
        acc = ACCOUNTS[CUR_ACC_INDEX]
        try:
            await acc(GetMessagesViewsRequest(peer=post_link.split('/')[0], id=[int(post_link.split('/')[1])], increment=True))
            cnt_success_views += 1
            Stamp(f"Viewed post {post_link} using account {acc.session.filename.split('_')[-1]}", 's')
        except Exception as e:
            Stamp(f"Failed to view post {post_link} using account {acc.session.filename.split('_')[-1]}: {e}", 'e')
        CUR_ACC_INDEX = (CUR_ACC_INDEX + 1) % len(ACCOUNTS)
        Sleep(SHORT_SLEEP, 0.5)
    Stamp('View increasing procedure finished', 'b')
    return cnt_success_views


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
                duration = (req['finish'] - req['start']).total_seconds()
                interval = duration / req['planned']
                elapsed = (datetime.now() - req['start']).total_seconds()
                expected = int(elapsed / interval)
                current = req.get('current', 0)
                to_add = expected - current
                if to_add > 0:
                    if req['order_type'] == 'Подписка':
                        cnt_success = await PerformSubscription(req['link'], to_add, req['channel_type'])
                    else:
                        cnt_success = await IncreasePostViews(req['link'], to_add)
                    req['current'] = current + cnt_success
            else:
                if req['current'] < req['planned']:
                    to_add = req['planned'] - req.get('current', 0)
                    if req['order_type'] == 'Подписка':
                        cnt_success = await PerformSubscription(req['link'], to_add, req['channel_type'])
                    else:
                        cnt_success = await IncreasePostViews(req['link'], to_add)
                    req['current'] += cnt_success
                else:
                    REQS_QUEUE.remove(req)
                    FINISHED_REQS.append(req)
                    SaveFinishedRequests(FINISHED_REQS)
                    BOT.send_message(req['initiator'].split(' ')[0], f"✅ Заявка выполнена:")
                    BOT.send_message(req['initiator'].split(' ')[0], PrintRequest(req), parse_mode='Markdown')
        Sleep(LONG_SLEEP, 0.3)


def PostView(message: telebot.types.Message) -> None:
    Stamp('Post link inserting procedure', 'i')
    if not re.match(LINK_FORMAT, message.text):
        if message.text == CANCEL_BTN[0]:
            ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
        else:
            ShowButtons(message, CANCEL_BTN, "❌ Ссылка на пост не похожа на корректную. "
                                              "Пожалуйста, проверьте формат ссылки "
                                              "(https://t.me/channel_name_or_hash/post_id)")
            BOT.register_next_step_handler(message, PostView)
    else:
        global CUR_REQ
        cut_link = '/'.join(message.text.split('/')[-2:])
        CUR_REQ = {'order_type': 'Просмотры', 'initiator': f'{message.from_user.id} ({message.from_user.username})', 'link': cut_link}
        ShowButtons(message, CANCEL_BTN, f'❔ Введите желаемое количество просмотров (доступно {len(ACCOUNTS)} аккаунтов):')
        BOT.register_next_step_handler(message, NumberInsertingProcedure)


def ChannelSub(message: telebot.types.Message) -> None:
    Stamp('Channel link inserting procedure', 'i')
    global CUR_REQ
    if message.text == CANCEL_BTN[0]:
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    elif not message.text[0] == '@' and not re.match(LINK_FORMAT, message.text):
        ShowButtons(message, CANCEL_BTN, "❌ Ссылка на канал не похожа на корректную. "
                                         "Пожалуйста, проверьте формат ссылки "
                                         "(https://t.me/channel_name_or_hash или @channel_name)")
        BOT.register_next_step_handler(message, ChannelSub)
    else:
        CUR_REQ = {'order_type': 'Подписка', 'initiator': f'{message.from_user.id} ({message.from_user.username})'}
        cut_link = message.text.split('/')[-1]
        if cut_link[0] == '@':
            CUR_REQ['channel_type'] = 'public'
            cut_link = cut_link[1:]
        elif cut_link[0] == '+':
            cut_link = cut_link[1:]
            CUR_REQ['channel_type'] = 'private'
        else:
            CUR_REQ['channel_type'] = 'public'
        CUR_REQ['link'] = cut_link
        ShowButtons(message, CANCEL_BTN, f'❔ Введите желаемое количество подписок'
                                               f'(доступно {len(ACCOUNTS)} аккаунтов):')
        BOT.register_next_step_handler(message, NumberInsertingProcedure)


def RequestPeriod(message: telebot.types.Message) -> None:
    Stamp('Time inserting procedure', 'i')
    try:
        if message.text == CANCEL_BTN[0]:
            ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
        else:
            if 0 < int(message.text) < MAX_MINS:
                CUR_REQ['start'] = datetime.now()
                CUR_REQ['finish'] = datetime.now() + timedelta(minutes=int(message.text))
                REQS_QUEUE.append(CUR_REQ)
                BOT.send_message(message.from_user.id, "🆗 Заявка принята. Начинаю выполнение заявки...")
                ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
            else:
                ShowButtons(message, CANCEL_BTN, "❌ Введено некорректное число. Попробуйте ещё раз:")
                BOT.register_next_step_handler(message, RequestPeriod)
    except ValueError:
        ShowButtons(message, CANCEL_BTN, "❌ Пожалуйста, введите только число. Попробуйте ещё раз:")
        BOT.register_next_step_handler(message, RequestPeriod)


def NumberInsertingProcedure(message: telebot.types.Message) -> None:
    Stamp('Number inserting procedure', 'i')
    try:
        if message.text == CANCEL_BTN[0]:
            ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
        else:
            if 0 < int(message.text) <= len(ACCOUNTS):
                CUR_REQ['planned'] = int(message.text)
                ShowButtons(message, CANCEL_BTN, "❔ Введите промежуток времени (в минутах), "
                                                       "в течение которого будет выполняться заявка:")
                BOT.register_next_step_handler(message, RequestPeriod)
            else:

                ShowButtons(message, CANCEL_BTN, "❌ Введено некорректное число. Попробуйте ещё раз:")
                BOT.register_next_step_handler(message, NumberInsertingProcedure)
    except ValueError:
        ShowButtons(message, CANCEL_BTN, "❌ Пожалуйста, введите только число. Попробуйте ещё раз:")
        BOT.register_next_step_handler(message, NumberInsertingProcedure)


def SendActiveRequests(message: telebot.types.Message) -> None:
    if REQS_QUEUE:
        BOT.send_message(message.from_user.id, f' ⏳ Показываю {len(REQS_QUEUE)} активные заявки:')
        for req in REQS_QUEUE:
            BOT.send_message(message.from_user.id, PrintRequest(req), parse_mode='Markdown')
    else:
        BOT.send_message(message.from_user.id, '🔍 Нет активных заявок')


def PrintRequest(req: dict) -> str:
    return f"*Начало*: {req['start'].strftime('%Y-%m-%d %H:%M')}\n" \
           f"*Конец*: {req['finish'].strftime('%Y-%m-%d %H:%M')}\n" \
           f"*Тип заявки*: {req['order_type']}\n" \
           f"*Желаемое количество*: {req['planned']}\n" \
           f"*Выполненное количество*: {req.get('current', 0)}\n" \
           f"*Ссылка*: {req['link']}\n" \
           f"*Инициатор заявки*: {req['initiator']}"


def SaveFinishedRequests(finished_requests: list) -> None:
    Stamp('Saving finished requests', 'i')
    serialized_requests = []
    for req in finished_requests:
        req_copy = req.copy()
        req_copy['start'] = req['start'].isoformat()
        req_copy['finish'] = req['finish'].isoformat()
        serialized_requests.append(req_copy)
    with open(FINISHED_REQS_FILE, 'w', encoding='utf-8') as file:
        json.dump(serialized_requests, file, ensure_ascii=False, indent=4)


def LoadFinishedRequests() -> list:
    Stamp('Trying to load finished requests', 'i')
    if os.path.exists(FINISHED_REQS_FILE):
        with open(FINISHED_REQS_FILE, 'r', encoding='utf-8') as file:
            if os.path.getsize(FINISHED_REQS_FILE) > 0:
                loaded_requests = json.load(file)
                for req in loaded_requests:
                    req['start'] = datetime.fromisoformat(req['start'])
                    req['finish'] = datetime.fromisoformat(req['finish'])
                return loaded_requests
            else:
                Stamp('Finished requests file is empty', 'i')
    return []


def SendFinishedRequests(message: telebot.types.Message) -> None:
    if FINISHED_REQS:
        BOT.send_message(message.from_user.id, f' 📋 Показываю {len(FINISHED_REQS)} выполненные заявки:')
        for req in FINISHED_REQS:
            BOT.send_message(message.from_user.id, PrintRequest(req), parse_mode='Markdown')
    else:
        BOT.send_message(message.from_user.id, '🔍 Нет выполненных заявок')


@BOT.message_handler(content_types=['text'])
def MessageAccept(message: telebot.types.Message) -> None:
    Stamp(f'User {message.from_user.id} requested {message.text}', 'i')
    if message.text == '/start':
        BOT.send_message(message.from_user.id, f'Привет, {message.from_user.first_name}!')
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    elif message.text == WELCOME_BTNS[0]:
        ShowButtons(message, CANCEL_BTN, '❔ Введите ссылку на канал (например, https://t.me/channel_name_or_hash):')
        BOT.register_next_step_handler(message, ChannelSub)
    elif message.text == WELCOME_BTNS[1]:
        ShowButtons(message, CANCEL_BTN, '❔ Отправьте ссылку на пост (например, https://t.me/channel_name_or_hash/post_id):')
        BOT.register_next_step_handler(message, PostView)
    elif message.text == WELCOME_BTNS[2]:
        SendActiveRequests(message)
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    elif message.text == WELCOME_BTNS[3]:
        SendFinishedRequests(message)
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    elif message.text == CANCEL_BTN[0]:
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    else:
        BOT.send_message(message.from_user.id, '❌ Я вас не понял...')
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')


if __name__ == '__main__':
    Main()
