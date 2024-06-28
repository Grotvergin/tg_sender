from source import *


async def Main() -> None:
    global FINISHED_REQS, AUTO_SUBS_DICT, AUTO_REPS_DICT
    FINISHED_REQS = LoadRequestsFromFile('finished', 'finished.json')
    AUTO_SUBS_DICT = LoadRequestsFromFile('automatic subs', 'auto_views.json')
    AUTO_REPS_DICT = LoadRequestsFromFile('automatic reps', 'auto_reps.json')
    loop = get_event_loop()
    refresh_task = create_task(RefreshEventHandler())
    process_task = create_task(ProcessRequests())
    auth_task = create_task(CheckRefreshAuth())
    try:
        await gather(refresh_task, process_task, auth_task)
    finally:
        loop.close()


def BotPolling():
    while True:
        try:
            BOT.polling(none_stop=True, interval=1)
        except Exception as e:
            Stamp(f'{e}', 'e')
            Stamp(format_exc(), 'e')


def WaitForCode() -> int | None:
    global CODE
    start = time()
    while not CODE:
        sleep(1)
        Stamp('Waiting for code', 'l')
        if (time() - start) > MAX_WAIT_CODE:
            return
    code = CODE
    CODE = None
    return code


async def CheckRefreshAuth() -> None:
    global ADMIN_CHAT_ID
    while True:
        if ADMIN_CHAT_ID is not None:
            Stamp('Admin chat ID is set, authorizing accounts', 'i')
            await AuthorizeAccounts()
            ADMIN_CHAT_ID = None
        await async_sleep(SHORT_SLEEP)


def AuthCallback(number: str) -> int:
    BOT.send_message(ADMIN_CHAT_ID, f'❗️Введите код для {number} в течение {MAX_WAIT_CODE} секунд:')
    code = WaitForCode()
    if not code:
        BOT.send_message(ADMIN_CHAT_ID, '❌ Превышено время ожидания кода для {number}!')
        raise TimeoutError('Too long code waiting')
    return code


async def AuthorizeAccounts() -> None:
    Stamp('Authorization procedure started', 'b')
    BOT.send_message(ADMIN_CHAT_ID, '🔸Начата процедура авторизации...\n')
    data = GetSector('A2', 'H500', BuildService(), 'Авторизованные', SHEET_ID)
    this_run_auth = [client.session.filename for client in ACCOUNTS]
    for index, account in enumerate(data):
        try:
            num = account[0]
            api_id = account[1]
            api_hash = account[2]
            password_tg = account[3] if account[3] != '-' else None
            ip = account[4]
            port = int(account[5])
            login = account[6]
            password_proxy = account[7]
        except IndexError:
            Stamp(f'Invalid account data: {account}', 'e')
            BOT.send_message(ADMIN_CHAT_ID, f'❌ Неверные данные для аккаунта в строке {index + 2}!')
            continue
        session = join(getcwd(), 'sessions', f'{num}')
        if session + '.session' in this_run_auth:
            Stamp(f'Account {num} already authorized', 's')
            continue
        else:
            Stamp(f'Processing account {num}', 'i')
            client = TelegramClient(session, api_id, api_hash, proxy=(SOCKS5, ip, port, True, login, password_proxy))
            try:
                await client.start(phone=num, password=password_tg, code_callback=lambda: AuthCallback(num))
                ACCOUNTS.append(client)
                Stamp(f'Account {num} authorized', 's')
                BOT.send_message(ADMIN_CHAT_ID, f'✅ Аккаунт {num} авторизован')
                Sleep(LONG_SLEEP, 0.5)
            except PhoneCodeInvalidError:
                BOT.send_message(ADMIN_CHAT_ID, f'❌ Неверный код для номера {num}.')
                Stamp(f'Invalid code for {num}', 'e')
                continue
            except PhoneCodeExpiredError:
                BOT.send_message(ADMIN_CHAT_ID, f'❌ Истекло время действия кода для номера {num}.')
                Stamp(f'Code expired for {num}', 'e')
                continue
            except SessionPasswordNeededError:
                BOT.send_message(ADMIN_CHAT_ID, f'❗️Требуется двухфакторная аутентификация для номера {num}.')
                Stamp(f'2FA needed for {num}', 'w')
                continue
            except PhoneNumberInvalidError:
                BOT.send_message(ADMIN_CHAT_ID, f'❌ Неверный номер телефона {num}.')
                Stamp(f'Invalid phone number {num}', 'e')
                continue
            except Exception as e:
                BOT.send_message(ADMIN_CHAT_ID, f'❌ Ошибка при старте клиента для {num}: {str(e)}')
                Stamp(f'Error while starting client for {num}: {e}, {format_exc()}', 'e')
                continue
    BOT.send_message(ADMIN_CHAT_ID, f'🔹Процедура завершена, авторизовано {len(ACCOUNTS)} аккаунтов\n')
    ShowButtons(ADMIN_CHAT_ID, WELCOME_BTNS, '❔ Выберите действие:')
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


async def PerformSubscription(link: str, amount: int, channel_type: str, acc_index: int = None) -> int:
    Stamp('Subscription procedure started', 'b')
    cnt_success_subs = 0
    global CUR_ACC_INDEX
    for _ in range(amount):
        if acc_index:
            acc = ACCOUNTS[acc_index]
        else:
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


async def RepostMessage(post_link: str, reposts_needed: int) -> int:
    Stamp('Reposting procedure started', 'b')
    cnt_success_reposts = 0
    global CUR_ACC_INDEX
    for _ in range(reposts_needed):
        acc = ACCOUNTS[CUR_ACC_INDEX]
        try:
            entity = await acc.get_entity(post_link.split('/')[0])
            message_id = int(post_link.split('/')[1])
            await acc.forward_messages('me', message_id, entity)
            cnt_success_reposts += 1
            Stamp(f"Reposted post {post_link} using account {acc.session.filename.split('_')[-1]}", 's')
        except Exception as e:
            Stamp(f"Failed to repost {post_link} using account {acc.session.filename.split('_')[-1]}: {e}", 'e')
        CUR_ACC_INDEX = (CUR_ACC_INDEX + 1) % len(ACCOUNTS)
        await AsyncSleep(SHORT_SLEEP, 0.5)
    Stamp('Reposting procedure finished', 'b')
    return cnt_success_reposts


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
                    elif req['order_type'] == 'Просмотры':
                        cnt_success = await IncreasePostViews(req['link'], to_add)
                    else:
                        cnt_success = await RepostMessage(req['link'], to_add)
                    req['current'] = current + cnt_success
            else:
                if req.get('current', 0) < req['planned']:
                    to_add = req['planned'] - req.get('current', 0)
                    if req['order_type'] == 'Подписка':
                        cnt_success = await PerformSubscription(req['link'], to_add, req['channel_type'])
                    elif req['order_type'] == 'Просмотры':
                        cnt_success = await IncreasePostViews(req['link'], to_add)
                    else:
                        cnt_success = await RepostMessage(req['link'], to_add)
                    req['current'] = req.get('current', 0) + cnt_success
                else:
                    REQS_QUEUE.remove(req)
                    FINISHED_REQS.append(req)
                    SaveRequestsToFile(FINISHED_REQS, 'finished', 'finished.json')
                    BOT.send_message(req['initiator'].split(' ')[-1], f"✅ Заявка выполнена:")
                    BOT.send_message(req['initiator'].split(' ')[-1], PrintRequest(req), parse_mode='HTML')
        await AsyncSleep(LONG_SLEEP, 0.5)


async def RefreshEventHandler():
    while True:
        channels = list(AUTO_SUBS_DICT.keys()) + list(AUTO_REPS_DICT.keys())
        if ACCOUNTS and channels:
            Stamp(f'Setting up event handler with channels {", ".join(channels)}', 'i')
            already_subscribed = await GetSubscribedChannels(ACCOUNTS[0])
            list_for_subscription = [chan for chan in channels if chan not in already_subscribed]
            for chan in list_for_subscription:
                await PerformSubscription(chan, 1, 'public', 0)
            ACCOUNTS[0].remove_event_handler(EventHandler)
            ACCOUNTS[0].add_event_handler(EventHandler, NewMessage(chats=channels))
            Stamp("Event handler for new messages set up", 's')
        else:
            Stamp("No accounts available/no need to set up event handler", 'w')
        await AsyncSleep(LONG_SLEEP * 3, 0.5)


async def GetSubscribedChannels(account: TelegramClient) -> list[str]:
    Stamp(f'Trying to get all channels for account', 'i')
    result = await account(GetDialogsRequest(
        offset_date=None,
        offset_id=0,
        offset_peer=InputPeerEmpty(),
        limit=1000,
        hash=0
    ))
    channels = []
    for chat in result.chats:
        if isinstance(chat, Channel):
            channels.append(chat.username)
    return channels


def ContainsLink(text: str) -> bool:
    url_pattern = compile(r'http[s]?')
    return bool(url_pattern.search(text))


async def EventHandler(event):
    Stamp(f'Trying to add automatic request for channel {event.chat.username}', 'i')
    dicts_list = ({'dict': AUTO_SUBS_DICT, 'order_type': 'Просмотры'}, {'dict': AUTO_REPS_DICT, 'order_type': 'Репосты'})
    user_id = None
    for item in dicts_list:
        dict_name = item['dict']
        order_type = item['order_type']
        if event.chat.username in dict_name:
            if order_type == 'Репосты' and ContainsLink(event.message.message):
                dict_name[event.chat.username]['annual'] = int(float(dict_name[event.chat.username]['annual']) / LINK_DECREASE_RATIO)
            rand_amount = randint(int((1 - (float(dict_name[event.chat.username]['spread']) / 100)) * dict_name[event.chat.username]['annual']),
                                  int((1 + (float(dict_name[event.chat.username]['spread']) / 100)) * dict_name[event.chat.username]['annual']))
            REQS_QUEUE.append({'order_type': order_type,
                               'initiator': f'Автоматическая от {dict_name[event.chat.username]["initiator"]}',
                               'link': f'{event.chat.username}/{event.message.id}',
                               'start': datetime.now().strftime(TIME_FORMAT),
                               'finish': (datetime.now() + timedelta(minutes=dict_name[event.chat.username]['time_limit'])).strftime(TIME_FORMAT),
                               'planned': rand_amount})
            user_id = dict_name[event.chat.username]['initiator'].split(' ')[-1]
    BOT.send_message(user_id, f'⚡️ Обнаружена новая публикация в канале {event.chat.username}, заявка создана')
    Stamp(f'Added automatic request for channel {event.chat.username}', 's')


def AcceptPost(message: Message, order_type: str) -> None:
    Stamp('Post link inserting procedure', 'i')
    if not match(LINK_FORMAT, message.text):
        if message.text == CANCEL_BTN[0]:
            ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
        else:
            ShowButtons(message, CANCEL_BTN, "❌ Ссылка на пост не похожа на корректную. "
                                             "Пожалуйста, проверьте формат ссылки (https://t.me/name/post_id)")
            BOT.register_next_step_handler(message, AcceptPost, order_type)
    else:
        global CUR_REQ
        cut_link = '/'.join(message.text.split('/')[-2:])
        CUR_REQ = {'order_type': order_type, 'initiator': f'{message.from_user.username} – {message.from_user.id}', 'link': cut_link}
        ShowButtons(message, CANCEL_BTN, f'❔ Введите желаемое количество (доступно {len(ACCOUNTS)} аккаунтов):')
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
        CUR_REQ = {'order_type': 'Подписка', 'initiator': f'{message.from_user.username} – {message.from_user.id}'}
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


def AutomaticChannelAction(message: Message, file: str) -> None:
    Stamp('Automatic channel link inserting procedure', 'i')
    if message.text == CANCEL_BTN[0]:
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    elif not message.text[0] == '@' and not match(LINK_FORMAT, message.text):
        ShowButtons(message, CANCEL_BTN, "❌ Ссылка на канал не похожа на корректную. "
                                         "Пожалуйста, проверьте формат ссылки "
                                         "(https://t.me/name или @name)")
        BOT.register_next_step_handler(message, AutomaticChannelAction, file)
    else:
        global CUR_REQ
        CUR_REQ = {'initiator': f'{message.from_user.username} – {message.from_user.id}'}
        cut_link = message.text.split('/')[-1]
        if cut_link[0] == '@':
            cut_link = cut_link[1:]
        CUR_REQ['link'] = cut_link
        ShowButtons(message, CANCEL_BTN, f'❔ Введите количество аккаунтов, которые '
                                         f'будут автоматически совершать действие с новой публикацией '
                                         f'(доступно {len(ACCOUNTS)} аккаунтов):')
        BOT.register_next_step_handler(message, AutomaticNumberProcedure, file)


def AutomaticNumberProcedure(message: Message, file: str) -> None:
    Stamp('Automatic number inserting procedure', 'i')
    try:
        if message.text == CANCEL_BTN[0]:
            ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
        else:
            if 0 < int(message.text) <= len(ACCOUNTS):
                CUR_REQ['annual'] = int(message.text)
                ShowButtons(message, CANCEL_BTN, "❔ Введите промежуток времени (в минутах), отведённый на действие")
                BOT.register_next_step_handler(message, AutomaticPeriod, file)
            else:
                ShowButtons(message, CANCEL_BTN, "❌ Введено некорректное число. Попробуйте ещё раз:")
                BOT.register_next_step_handler(message, AutomaticNumberProcedure, file)
    except ValueError:
        ShowButtons(message, CANCEL_BTN, "❌ Пожалуйста, введите только число. Попробуйте ещё раз:")
        BOT.register_next_step_handler(message, AutomaticNumberProcedure, file)


def InsertSpread(message: Message, path: str) -> None:
    Stamp('Automatic spread inserting procedure', 'i')
    try:
        if message.text == CANCEL_BTN[0]:
            ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
        else:
            if 0 <= int(message.text) < 100:
                CUR_REQ['spread'] = int(message.text)
                CUR_REQ['approved'] = datetime.now().strftime(TIME_FORMAT)
                record = {'initiator': CUR_REQ['initiator'],
                          'time_limit': CUR_REQ['time_limit'],
                          'approved': CUR_REQ['approved'],
                          'annual': CUR_REQ['annual'],
                          'spread': CUR_REQ['spread']}
                if path == 'auto_views.json':
                    AUTO_SUBS_DICT[CUR_REQ['link']] = record
                    SaveRequestsToFile(AUTO_SUBS_DICT, 'automatic subs', 'auto_views.json')
                else:
                    AUTO_REPS_DICT[CUR_REQ['link']] = record
                    SaveRequestsToFile(AUTO_REPS_DICT, 'automatic reps', 'auto_reps.json')
                BOT.send_message(message.from_user.id, f"🆗 Заявка принята. Буду следить за обновлениями в канале {CUR_REQ['link']}...")
                ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
            else:
                ShowButtons(message, CANCEL_BTN, "❌ Введено некорректное число. Попробуйте ещё раз:")
                BOT.register_next_step_handler(message, InsertSpread, path)
    except ValueError:
        ShowButtons(message, CANCEL_BTN, "❌ Пожалуйста, введите только число. Попробуйте ещё раз:")
        BOT.register_next_step_handler(message, InsertSpread, path)


def AutomaticPeriod(message: Message, path: str) -> None:
    Stamp('Automatic time inserting procedure', 'i')
    try:
        if message.text == CANCEL_BTN[0]:
            ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
        else:
            if 0 < int(message.text) < MAX_MINS:
                CUR_REQ['time_limit'] = int(message.text)
                BOT.send_message(message.from_user.id, '❔ Введите разброс (в %, от 0 до 100), с которым рассчитается количество')
                BOT.register_next_step_handler(message, InsertSpread, path)
            else:
                ShowButtons(message, CANCEL_BTN, "❌ Введено некорректное число. Попробуйте ещё раз:")
                BOT.register_next_step_handler(message, AutomaticPeriod, path)
    except ValueError:
        ShowButtons(message, CANCEL_BTN, "❌ Пожалуйста, введите только число. Попробуйте ещё раз:")
        BOT.register_next_step_handler(message, AutomaticPeriod, path)


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
            BOT.send_message(message.from_user.id, PrintRequest(req), parse_mode='HTML')
    else:
        BOT.send_message(message.from_user.id, '🔍 Нет активных заявок')


def PrintRequest(req: dict) -> str:
    return (f"<b>Начало</b>: {req['start']}\n"
                          f"<b>Конец</b>: {req['finish']}\n"
                          f"<b>Тип</b>: {req['order_type']}\n"
                          f"<b>Желаемое</b>: {req['planned']}\n"
                          f"<b>Выполненное</b>: {req.get('current', 0)}\n"
                          f"<b>Ссылка</b>: {req['link']}\n"
                          f"<b>Инициатор</b>: {req['initiator']}")


def PrintAutomaticRequest(chan: str, data: dict) -> str:
    return (f"<b>Канал</b>: {chan}\n"
                          f"<b>Инициатор</b>: {data[chan]['initiator']}\n"
                          f"<b>Временной интервал</b>: {data[chan]['time_limit']}\n"
                          f"<b>Создана</b>: {data[chan]['approved']}\n"
                          f"<b>На публикацию</b>: {data[chan]['annual']}\n"
                          f"<b>Разброс</b>: {data[chan]['spread']}%")


def SendFinishedRequests(message: Message) -> None:
    if FINISHED_REQS:
        BOT.send_message(message.from_user.id, f' 📋 Показываю {len(FINISHED_REQS)} выполненные заявки:')
        for req in FINISHED_REQS:
            BOT.send_message(message.from_user.id, PrintRequest(req), parse_mode='HTML')
    else:
        BOT.send_message(message.from_user.id, '🔍 Нет выполненных заявок')


def DeleteAutomaticRequest(message: Message, path: str) -> None:
    if message.text in AUTO_SUBS_DICT.keys() and path == 'auto_views.json':
        del AUTO_SUBS_DICT[message.text]
        SaveRequestsToFile(AUTO_SUBS_DICT, 'automatic subs', path)
        BOT.send_message(message.from_user.id, f'✅ Автоматическая заявка на просмотры для канала {message.text} удалена')
    elif message.text in AUTO_REPS_DICT.keys() and path == 'auto_reps.json':
        del AUTO_REPS_DICT[message.text]
        SaveRequestsToFile(AUTO_REPS_DICT, 'automatic reps', path)
        BOT.send_message(message.from_user.id, f'✅ Автоматическая заявка на репосты для канала {message.text} удалена')
    else:
        BOT.send_message(message.from_user.id, '❌ Не нашёл автоматической заявки на такой канал')
    ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')


def AutomaticChoice(message: Message) -> None:
    if message.text == AUTO_CHOICE[0]:
        ShowButtons(message, AUTO_BTNS, '❔ Выберите действие:')
        BOT.register_next_step_handler(message, AutomaticChannelDispatcher, 'auto_views.json')
    elif message.text == AUTO_CHOICE[1]:
        ShowButtons(message, AUTO_BTNS, '❔ Выберите действие:')
        BOT.register_next_step_handler(message, AutomaticChannelDispatcher, 'auto_reps.json')
    elif message.text == AUTO_CHOICE[2]:
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    else:
        BOT.send_message(message.from_user.id, '❌ Я вас не понял...')
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')


def AutomaticChannelDispatcher(message: Message, file: str) -> None:
    if message.text == AUTO_BTNS[0]:
        ShowButtons(message, CANCEL_BTN, '❔ Введите ссылку на канал, для которого будет создана'
                                         'автоматическая заявка (https://t.me/name или @name):')
        BOT.register_next_step_handler(message, AutomaticChannelAction, file)
    elif message.text == AUTO_BTNS[1]:
        BOT.send_message(message.from_user.id, '❔ Введите имя канала, для которого нужно отменить '
                                               'автоматическую заявку (name):')
        BOT.register_next_step_handler(message, DeleteAutomaticRequest, file)
    elif message.text == AUTO_BTNS[2]:
        data = AUTO_SUBS_DICT if file == 'auto_views.json' else AUTO_REPS_DICT
        if data.keys():
            for chan in data.keys():
                BOT.send_message(message.from_user.id, PrintAutomaticRequest(chan, data), parse_mode='HTML')
        else:
            BOT.send_message(message.from_user.id, '🔍 Нет автоматических заявок')
        ShowButtons(message, AUTO_BTNS, '❔ Выберите действие:')
        BOT.register_next_step_handler(message, AutomaticChannelDispatcher, file)
    elif message.text == AUTO_BTNS[3]:
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    else:
        BOT.send_message(message.from_user.id, '❌ Я вас не понял...')
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')


def SingleChoice(message: Message) -> None:
    if message.text == SINGLE_BTNS[0]:
        SendActiveRequests(message)
        ShowButtons(message, SINGLE_BTNS, '❔ Выберите действие:')
        BOT.register_next_step_handler(message, SingleChoice)
    elif message.text == SINGLE_BTNS[1]:
        SendFinishedRequests(message)
        ShowButtons(message, SINGLE_BTNS, '❔ Выберите действие:')
        BOT.register_next_step_handler(message, SingleChoice)
    elif message.text == SINGLE_BTNS[2]:
        ShowButtons(message, CANCEL_BTN, '❔ Введите ссылку на канал (https://t.me/name_or_hash или @name):')
        BOT.register_next_step_handler(message, ChannelSub)
    elif message.text == SINGLE_BTNS[3]:
        ShowButtons(message, CANCEL_BTN, '❔ Отправьте ссылку на пост (https://t.me/name/post_id):')
        BOT.register_next_step_handler(message, AcceptPost, 'Просмотры')
    elif message.text == SINGLE_BTNS[4]:
        ShowButtons(message, CANCEL_BTN, '❔ Отправьте ссылку на пост (https://t.me/name/post_id):')
        BOT.register_next_step_handler(message, AcceptPost, 'Репосты')
    elif message.text == SINGLE_BTNS[5]:
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    else:
        BOT.send_message(message.from_user.id, '❌ Я вас не понял...')
        ShowButtons(message, SINGLE_BTNS, '❔ Выберите действие:')
        BOT.register_next_step_handler(message, SingleChoice)


@BOT.message_handler(content_types=['text'])
def MessageAccept(message: Message) -> None:
    global CODE, ADMIN_CHAT_ID
    Stamp(f'User {message.from_user.id} requested {message.text}', 'i')
    if message.text == '/start':
        BOT.send_message(message.from_user.id, f'Привет, {message.from_user.first_name}!')
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    elif message.text == WELCOME_BTNS[0]:
        ShowButtons(message, SINGLE_BTNS, '❔ Выберите действие:')
        BOT.register_next_step_handler(message, SingleChoice)
    elif message.text == WELCOME_BTNS[1]:
        ShowButtons(message, AUTO_CHOICE, '❔ Выберите действие:')
        BOT.register_next_step_handler(message, AutomaticChoice)
    elif message.text == WELCOME_BTNS[2]:
        ADMIN_CHAT_ID = message.from_user.id
    elif message.text == CANCEL_BTN[0]:
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')
    elif message.text.isdigit() and len(message.text) == 5:
        CODE = int(message.text)
    else:
        BOT.send_message(message.from_user.id, '❌ Я вас не понял...')
        ShowButtons(message, WELCOME_BTNS, '❔ Выберите действие:')


if __name__ == '__main__':
    Thread(target=BotPolling, daemon=True).start()
    run(Main())
