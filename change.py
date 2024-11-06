from telebot.apihelper import proxy

import source
from source import BOT, IMG_PATH, LEFT_CORNER, RIGHT_CORNER, URL_BUY_PROXY, URL_RECEIVE_PROXY
from common import Stamp, UploadData, GetSector, BuildService
from emulator import PressButton, ExitFromAccount
from secret import PASSWORD, SHEET_ID, SHEET_NAME, MY_TG_ID
from generator import GenerateRandomRussianName, GenerateRandomDescription, GetRandomProfilePicture
# ---
from os import remove, getcwd
from os.path import split, join
from random import randint
from asyncio import sleep as async_sleep
from re import search
# ---
from appium.webdriver.common.appiumby import AppiumBy
from requests import get, RequestException, post
from telethon.sync import TelegramClient
from telethon.tl.functions.account import UpdateProfileRequest, SetPrivacyRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest
from telethon.tl.functions.contacts import ImportContactsRequest
from telethon.tl.types import (InputPrivacyValueDisallowAll,
                               InputPrivacyKeyPhoneNumber,
                               InputPrivacyKeyPhoneCall,
                               InputPrivacyKeyChatInvite,
                               InputPrivacyKeyStatusTimestamp,
                               InputPhoneContact)


def buyProxy(user_id: int):
    Stamp('Buying proxy', 'i')
    BOT.send_message(user_id, '🔒 Покупаю прокси...')
    payload = {'PurchaseBilling':
        {
            "count": 1,
            "duration": 30,
            'type': 102,
            'country': 'ru'
        }
    }
    try:
        response = post(URL_BUY_PROXY, json=payload)
        response.raise_for_status()
        data = response.json()
        if data.get('success'):
            Stamp('Proxy bought', 's')
            BOT.send_message(user_id, '✅ Прокси куплен')
        else:
            error_code = data.get('code', 'UNKNOWN_ERROR')
            Stamp(f'Error while buying proxy: {error_code}', 'e')
            BOT.send_message(user_id, f'❌ Ошибка при покупке прокси: {error_code}')
            raise Exception(f"Error code: {error_code}")
    except RequestException as e:
        Stamp(f'HTTP Request failed: {e}', 'e')
        BOT.send_message(user_id, '❌ Ошибка при покупке прокси. Проверьте соединение.')


def receiveProxyInfo(user_id: str) -> tuple:
    Stamp('Receiving proxy', 'i')
    BOT.send_message(user_id, '🔒 Получаю данные о прокси...')
    payload = {
        "type": "ipv4-shared",
        "proxy_type": "server",
        "page": 1,
        "page_size": 1,
        "sort": 0
    }
    try:
        response = post(URL_RECEIVE_PROXY, json=payload)
        response.raise_for_status()
        data = response.json()
        if data.get('success'):
            Stamp('Proxy received', 's')
            BOT.send_message(user_id, '🟢 Прокси получен')
            cur = data['list']['data'][0]
            proxy = (2, cur['ip'], cur['socks_port'], True, cur['login'], cur['password'])
            return proxy
        else:
            error_code = data.get('message', 'UNKNOWN_ERROR')
            Stamp(f'Error while receiving proxy: {error_code}', 'e')
            BOT.send_message(user_id, f'❌ Ошибка при покупке прокси: {error_code}')
            raise Exception(f"Error code: {error_code}")
    except RequestException as e:
        Stamp(f'HTTP Request failed: {e}', 'e')
        BOT.send_message(user_id, '❌ Ошибка при получении прокси. Проверьте соединение.')


async def CheckProfileChange() -> None:
    while True:
        if source.ACC_TO_CHANGE:
            num = source.ACC_TO_CHANGE["num"]
            api_id = source.ACC_TO_CHANGE["api_id"]
            api_hash = source.ACC_TO_CHANGE["api_hash"]
            user_id = source.ACC_TO_CHANGE["user_id"]
            driver = source.ACC_TO_CHANGE["driver"]
            Stamp('Account to change found', 'i')
            BOT.send_message(user_id, '🔄 Изменяю профиль...')
            try:
                buyProxy(user_id)
                proxy = receiveProxyInfo(user_id)
                session = join(getcwd(), 'sessions', f'{num}')
                client = TelegramClient(session, api_id, api_hash)
                await client.start(phone=num, password=PASSWORD, code_callback=lambda: emuAuthCallback(driver))
                Stamp(f'Account {num} authorized', 's')
                BOT.send_message(user_id, f'✅ Аккаунт {num} авторизован')
                source.ACCOUNTS.append(client)
                await SetProfileInfo(client, user_id)
                await SetProfilePicture(client, user_id)
                await AddContacts(client, 50, user_id)
                await UpdatePrivacySettings(client, user_id)
                srv = BuildService()
                row = len(GetSector(LEFT_CORNER, RIGHT_CORNER, srv, SHEET_NAME, SHEET_ID)) + 2
                UploadData([[num[1:], api_id, api_hash, PASSWORD, proxy[1], proxy[2], proxy[4], proxy[5]]], SHEET_NAME, SHEET_ID, srv, row)
                Stamp(f'Data for number {num} added to the table', 's')
                BOT.send_message(user_id, f'📊 Данные для номера {num} занесены в таблицу')
                ExitFromAccount(driver)
                source.ACC_TO_CHANGE = None
            except Exception as e:
                Stamp(f'Error while changing account: {e}', 'e')
                BOT.send_message(user_id, f'❌ Произошла ошибка при изменении данных: {e}')
        await async_sleep(source.SHORT_SLEEP)


def emuAuthCallback(driver) -> int:
    PressButton(driver, "android.view.ViewGroup", 'Message with session code', 3, by=AppiumBy.CLASS_NAME)
    element = driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().textContains("Код для входа в Telegram")')
    match = search(r'\b\d{5}\b', element.text)
    PressButton(driver, '//android.widget.ImageView[@content-desc="Go back"]', 'Go back', 3)
    if match:
        code = int(match.group())
        Stamp(f'Code {code} found', 's')
        return code
    else:
        Stamp('No code found in message', 'e')
        raise ValueError("Код не найден в сообщении")


def FindAccountByNumber(num: int) -> TelegramClient | None:
    for acc in source.ACCOUNTS:
        if int(split(acc.session.filename)[-1][:-8]) == num:
            return acc
    return None


async def SetProfilePicture(client: TelegramClient, user_id: int) -> None:
    Stamp('Setting profile picture', 'i')
    BOT.send_message(user_id, '🖼 Изменяю фотографию профиля...')
    GetRandomProfilePicture(user_id)
    file = await client.upload_file(IMG_PATH)
    await client(UploadProfilePhotoRequest(file=file))
    remove(IMG_PATH)


async def SetProfileInfo(client: TelegramClient, user_id: int) -> None:
    Stamp('Setting profile info', 'i')
    BOT.send_message(user_id, '📝 Изменяю ФИО и описание...')
    first_name, last_name = GenerateRandomRussianName()
    await client(UpdateProfileRequest(about=GenerateRandomDescription(),
                                      first_name=first_name,
                                      last_name=last_name))


async def AddContacts(client: TelegramClient, num: int, user_id: int) -> None:
    Stamp(f'Adding {num} contacts', 'i')
    BOT.send_message(user_id, f'📞 Добавляю контакты...')
    contacts = []
    for _ in range(num):
        first_name, last_name = GenerateRandomRussianName()
        phone = f'+7{randint(900, 999)}{randint(1000000, 9999999)}'
        contact = InputPhoneContact(client_id=randint(100000, 999999),
                                    phone=phone,
                                    first_name=first_name,
                                    last_name=last_name)
        contacts.append(contact)
    await client(ImportContactsRequest(contacts))


async def UpdatePrivacySettings(client: TelegramClient, user_id: int) -> None:
    Stamp('Updating privacy settings', 'i')
    BOT.send_message(user_id, '🔒 Обновляю настройки приватности...')
    await client(SetPrivacyRequest(
        key=InputPrivacyKeyPhoneNumber(),
        rules=[InputPrivacyValueDisallowAll()]
    ))
    await client(SetPrivacyRequest(
        key=InputPrivacyKeyPhoneCall(),
        rules=[InputPrivacyValueDisallowAll()]
    ))
    await client(SetPrivacyRequest(
        key=InputPrivacyKeyStatusTimestamp(),
        rules=[InputPrivacyValueDisallowAll()]
    ))
    await client(SetPrivacyRequest(
        key=InputPrivacyKeyChatInvite(),
        rules=[InputPrivacyValueDisallowAll()]
    ))
