from source import *

#TODO ОТМЕНА/АКТИВНЫЕ АВТОМАТИЧЕСКОЙ ПОДПИСКИ
#TODO ПРОКИНУТЬ КОД ЧЕРЕЗ БОТА
#TODO ВОЗМОЖНОСТЬ ОБНОВИТЬ АВТОРИЗАЦИЮ
#TODO ПОДПИСКА СЛЕДЯЩИМ АККАУНТОМ НА КАНАЛ


async def Main() -> None:
    await AuthorizeAccounts()
    global FINISHED_REQS, AUTO_REQS_DICT
    FINISHED_REQS = LoadRequestsFromFile('finished', 'finished.json')
    AUTO_REQS_DICT = LoadRequestsFromFile('automatic', 'auto.json')
    loop = get_event_loop()
    refresh_task = create_task(RefreshEventHandler())
    process_task = create_task(ProcessRequests())
    try:
        await gather(refresh_task, process_task)
    finally:
        loop.close()


def BotPolling():
    while True:
        try:
            BOT.polling(none_stop=True, interval=1)
        except Exception as e:
            Stamp(f'{e}', 'e')
            Stamp(format_exc(), 'e')


async def AuthorizeAccounts():
    Stamp('Authorization procedure started', 'b')
    data = GetSector('A2', 'D500', BuildService(), 'Авторизованные', SHEET_ID)
    for account in data:
        session = join(getcwd(), 'sessions', f'session_{account[0]}')
        client = TelegramClient(session, account[1], account[2])
        Stamp(f'Account {account[0]}', 'i')
        try:
            password = account[3] if account[3] != '-' else None
        except IndexError:
            password = None
        await client.start(phone=account[0], password=password)
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
            finish = datetime.strptime(req['finish'], TIME_FORMAT)
            start = datetime.strptime(req['start'], TIME_FORMAT)
            if datetime.now() < finish:
                duration = (finish - start).total_seconds()
                interval = duration / req['planned']
                elapsed = (datetime.now() - start).total_seconds()
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
                if req.get('current', 0) < req['planned']:
                    to_add = req['planned'] - req.get('current', 0)
                    if req['order_type'] == 'Подписка':
                        cnt_success = await PerformSubscription(req['link'], to_add, req['channel_type'])
                    else:
                        cnt_success = await IncreasePostViews(req['link'], to_add)
                    req['current'] = req.get('current', 0) + cnt_success
                else:
                    REQS_QUEUE.remove(req)
                    FINISHED_REQS.append(req)
                    SaveRequestsToFile(FINISHED_REQS, 'finished', 'finished.json')
                    BOT.send_message(req['initiator'].split(' ')[-2], f"✅ Заявка выполнена:")
                    BOT.send_message(req['initiator'].split(' ')[-2], PrintRequest(req), parse_mode='Markdown')
        await AsyncSleep(LONG_SLEEP, 0.5)


async def RefreshEventHandler():
    while True:
        Stamp(f'Setting up event handler with channels {", ".join(AUTO_REQS_DICT.keys())}', 'i')
        if ACCOUNTS:
            ACCOUNTS[0].add_event_handler(EventHandler, events.NewMessage(chats=list(AUTO_REQS_DICT.keys())))
            Stamp("Event handler for new messages set up", 's')
        else:
            Stamp("No accounts available to set up event handler", 'e')
        await AsyncSleep(LONG_SLEEP * 5)


async def EventHandler(event):
    Stamp(f'Trying to add automatic request for channel {event.chat.username}', 'i')
    REQS_QUEUE.append({
        'order_type': 'Просмотры',
        'initiator': f'Автоматическая от {AUTO_REQS_DICT[event.chat.username]['initiator']}',
        'link': f'{event.chat.username}/{event.message.id}',
        'start': datetime.now().strftime(TIME_FORMAT),
        'finish': (datetime.now() + timedelta(minutes=AUTO_REQS_DICT[event.chat.username]['time_limit'])).strftime(TIME_FORMAT),
        'planned': AUTO_REQS_DICT[event.chat.username]['annual_subs'],
    })
    BOT.send_message(AUTO_REQS_DICT[event.chat.username]['initiator'].split(' ')[0],
                     f'⚡️ Обнаружена новая публикация в канале {event.chat.username}, заявка на просмотры создана')
    Stamp(f'Added automatic request for channel {event.chat.username}', 's')


def PostView(message: Message) -> None:
    Stamp('Post link inserting procedure', 'i')
    if not match(LINK_FORMAT, message.text):
        if message.text == CANCEL_BTN[0]:
            ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
        else:
            ShowButtons(message, CANCEL_BTN, "❌ Ссылка на пост не похожа на корректную. "
                                              "Пожалуйста, проверьте формат ссылки (https://t.me/name/post_id)")
            BOT.register_next_step_handler(message, PostView)
    else:
        global CUR_REQ
        cut_link = '/'.join(message.text.split('/')[-2:])
        CUR_REQ = {'order_type': 'Просмотры', 'initiator': f'{message.from_user.id} ({message.from_user.username})', 'link': cut_link}
        ShowButtons(message, CANCEL_BTN, f'❔ Введите желаемое количество просмотров (доступно {len(ACCOUNTS)} аккаунтов):')
        BOT.register_next_step_handler(message, NumberInsertingProcedure)


def ChannelSub(message: Message) -> None:
    Stamp('Channel link inserting procedure', 'i')
    global CUR_REQ
    if message.text == CANCEL_BTN[0]:
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    elif not message.text[0] == '@' and not match(LINK_FORMAT, message.text):
        ShowButtons(message, CANCEL_BTN, "❌ Ссылка на канал не похожа на корректную. "
                                         "Пожалуйста, проверьте формат ссылки "
                                         "(https://t.me/name_or_hash или @name)")
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


def AutomaticChannelView(message: Message) -> None:
    Stamp('Automatic channel link inserting procedure', 'i')
    if message.text == CANCEL_BTN[0]:
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    elif not message.text[0] == '@' and not match(LINK_FORMAT, message.text):
        ShowButtons(message, CANCEL_BTN, "❌ Ссылка на канал не похожа на корректную. "
                                         "Пожалуйста, проверьте формат ссылки "
                                         "(https://t.me/name или @name)")
        BOT.register_next_step_handler(message, AutomaticChannelView)
    else:
        global CUR_REQ
        CUR_REQ = {'initiator': f'{message.from_user.id} ({message.from_user.username})'}
        cut_link = message.text.split('/')[-1]
        if cut_link[0] == '@':
            cut_link = cut_link[1:]
        CUR_REQ['link'] = cut_link
        ShowButtons(message, CANCEL_BTN, f'❔ Введите количество аккаунтов, которые '
                                         f'будут автоматически просматривать новую публикацию '
                                               f'(доступно {len(ACCOUNTS)} аккаунтов):')
        BOT.register_next_step_handler(message, AutomaticNumberProcedure)


def AutomaticNumberProcedure(message: Message) -> None:
    Stamp('Automatic number inserting procedure', 'i')
    try:
        if message.text == CANCEL_BTN[0]:
            ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
        else:
            if 0 < int(message.text) <= len(ACCOUNTS):
                CUR_REQ['annual_subs'] = int(message.text)
                ShowButtons(message, CANCEL_BTN, "❔ Введите промежуток времени (в минутах), "
                                                 f"по истечении которого {int(message.text)} аккаунтов просмотрят новую публикацию:")
                BOT.register_next_step_handler(message, AutomaticPeriod)
            else:
                ShowButtons(message, CANCEL_BTN, "❌ Введено некорректное число. Попробуйте ещё раз:")
                BOT.register_next_step_handler(message, AutomaticNumberProcedure)
    except ValueError:
        ShowButtons(message, CANCEL_BTN, "❌ Пожалуйста, введите только число. Попробуйте ещё раз:")
        BOT.register_next_step_handler(message, AutomaticNumberProcedure)


def AutomaticPeriod(message: Message) -> None:
    Stamp('Automatic time inserting procedure', 'i')
    try:
        if message.text == CANCEL_BTN[0]:
            ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
        else:
            if 0 < int(message.text) < MAX_MINS:
                CUR_REQ['approved'] = datetime.now().strftime(TIME_FORMAT)
                CUR_REQ['time_limit'] = int(message.text)
                AUTO_REQS_DICT[CUR_REQ['link']] = {'initiator': CUR_REQ['initiator'],
                                                   'time_limit': CUR_REQ['time_limit'],
                                                   'approved': CUR_REQ['approved'],
                                                   'annual_subs': CUR_REQ['annual_subs']}
                SaveRequestsToFile(AUTO_REQS_DICT, 'automatic', 'auto.json')
                BOT.send_message(message.from_user.id, f"🆗 Заявка принята. Буду следить за обновлениями в канале {CUR_REQ['link']}...")
                ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
            else:
                ShowButtons(message, CANCEL_BTN, "❌ Введено некорректное число. Попробуйте ещё раз:")
                BOT.register_next_step_handler(message, AutomaticPeriod)
    except ValueError:
        ShowButtons(message, CANCEL_BTN, "❌ Пожалуйста, введите только число. Попробуйте ещё раз:")
        BOT.register_next_step_handler(message, AutomaticPeriod)


def SaveRequestsToFile(requests: list | dict, msg: str, file: str) -> None:
    Stamp(f'Saving {msg} requests', 'i')
    with open(file, 'w', encoding='utf-8') as f:
        dump(requests, f, ensure_ascii=False, indent=4)


def LoadRequestsFromFile(msg: str, file: str) -> list | dict:
    Stamp(f'Trying to load {msg} requests', 'i')
    if exists(file):
        with open(file, 'r', encoding='utf-8') as f:
            if getsize(file) > 0:
                return load(f)
            else:
                Stamp(f'File with {msg} requests is empty', 'w')
    else:
        Stamp(f'No file with {msg} requests found', 'w')
    return []


def RequestPeriod(message: Message) -> None:
    Stamp('Time inserting procedure', 'i')
    try:
        if message.text == CANCEL_BTN[0]:
            ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
        else:
            if 0 < int(message.text) < MAX_MINS:
                CUR_REQ['start'] = datetime.now().strftime(TIME_FORMAT)
                CUR_REQ['finish'] = (datetime.now() + timedelta(minutes=int(message.text))).strftime(TIME_FORMAT)
                REQS_QUEUE.append(CUR_REQ)
                BOT.send_message(message.from_user.id, "🆗 Заявка принята. Начинаю выполнение заявки...")
                ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
            else:
                ShowButtons(message, CANCEL_BTN, "❌ Введено некорректное число. Попробуйте ещё раз:")
                BOT.register_next_step_handler(message, RequestPeriod)
    except ValueError:
        ShowButtons(message, CANCEL_BTN, "❌ Пожалуйста, введите только число. Попробуйте ещё раз:")
        BOT.register_next_step_handler(message, RequestPeriod)


def NumberInsertingProcedure(message: Message) -> None:
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


def SendActiveRequests(message: Message) -> None:
    if REQS_QUEUE:
        BOT.send_message(message.from_user.id, f' ⏳ Показываю {len(REQS_QUEUE)} активные заявки:')
        for req in REQS_QUEUE:
            BOT.send_message(message.from_user.id, PrintRequest(req), parse_mode='Markdown')
    else:
        BOT.send_message(message.from_user.id, '🔍 Нет активных заявок')


def PrintRequest(req: dict) -> str:
    return f"*Начало*: {req['start']}\n" \
           f"*Конец*: {req['finish']}\n" \
           f"*Тип заявки*: {req['order_type']}\n" \
           f"*Желаемое количество*: {req['planned']}\n" \
           f"*Выполненное количество*: {req.get('current', 0)}\n" \
           f"*Ссылка*: {req['link']}\n" \
           f"*Инициатор заявки*: {req['initiator']}"


def SendFinishedRequests(message: Message) -> None:
    if FINISHED_REQS:
        BOT.send_message(message.from_user.id, f' 📋 Показываю {len(FINISHED_REQS)} выполненные заявки:')
        for req in FINISHED_REQS:
            BOT.send_message(message.from_user.id, PrintRequest(req), parse_mode='Markdown')
    else:
        BOT.send_message(message.from_user.id, '🔍 Нет выполненных заявок')


@BOT.message_handler(content_types=['text'])
def MessageAccept(message: Message) -> None:
    Stamp(f'User {message.from_user.id} requested {message.text}', 'i')
    if message.text == '/start':
        BOT.send_message(message.from_user.id, f'Привет, {message.from_user.first_name}!')
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    elif message.text == WELCOME_BTNS[0]:
        ShowButtons(message, CANCEL_BTN, '❔ Введите ссылку на канал (https://t.me/name_or_hash или @name):')
        BOT.register_next_step_handler(message, ChannelSub)
    elif message.text == WELCOME_BTNS[1]:
        ShowButtons(message, CANCEL_BTN, '❔ Отправьте ссылку на пост (https://t.me/name/post_id):')
        BOT.register_next_step_handler(message, PostView)
    elif message.text == WELCOME_BTNS[2]:
        SendActiveRequests(message)
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    elif message.text == WELCOME_BTNS[3]:
        SendFinishedRequests(message)
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    elif message.text == WELCOME_BTNS[4]:
        ShowButtons(message, CANCEL_BTN, '❔ Введите ссылку на канал,для которого будут '
                                         'отслеживаться новые публикации (https://t.me/name или @name):')
        BOT.register_next_step_handler(message, AutomaticChannelView)
    elif message.text == CANCEL_BTN[0]:
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    else:
        BOT.send_message(message.from_user.id, '❌ Я вас не понял...')
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')


if __name__ == '__main__':
    Thread(target=BotPolling, daemon=True).start()
    run(Main())
