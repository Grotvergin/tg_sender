import source
from source import BOT, IMG_PATH, LEFT_CORNER, RIGHT_CORNER
from common import Stamp, UploadData, GetSector, BuildService
from emulator import PressButton, ExitFromAccount
from secret import PASSWORD, PROXY_KEY, SHEET_ID, SHEET_NAME
from generator import GenerateRandomRussianName, GenerateRandomDescription, GetRandomProfilePicture
# ---
from os import remove, getcwd
from os.path import split, join
from random import randint
from asyncio import sleep as async_sleep
from re import search
# ---
from appium.webdriver.common.appiumby import AppiumBy
from requests import get, RequestException
from socks import SOCKS5
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
    url = f"https://proxy6.net/api/{PROXY_KEY}/buy"
    params = {
        'count': 1,
        'period': 30,
        'country': 'id',
        'version': 4,
        'type': 'socks'
    }
    try:
        response = get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if data['status'] == 'yes':
            proxy_data = list(data['list'].values())[0]
            proxy = (
                SOCKS5,
                proxy_data['host'],
                proxy_data['port'],
                True,
                proxy_data['user'],
                proxy_data['pass']
            )
            Stamp(f'Proxy bought: {proxy[1]}:{proxy[2]}', 's')
            BOT.send_message(user_id, f'✅ Прокси куплен: {proxy[1]}:{proxy[2]}')
            return proxy
        else:
            Stamp(f'Error while buying proxy: {data}', 'e')
            BOT.send_message(user_id, f'❌ Ошибка при покупке прокси')
            raise Exception(f"Error: {data}")
    except RequestException as e:
        Stamp(f'HTTP Request failed: {e}', 'e')
        return
    except Exception as e:
        Stamp(f'An error occurred: {e}', 'e')
        return


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
            proxy = buyProxy(user_id)
            # proxy = (2, '181.177.100.240', '8000', True, 'd0qV1e', '16BRMs')
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
            UploadData([[num, api_id, api_hash, PASSWORD, proxy[1], proxy[2], proxy[4], proxy[5]]], SHEET_NAME, SHEET_ID, srv, row)
            Stamp(f'Data for number {num} added to the table', 's')
            BOT.send_message(user_id, f'📊 Данные для номера {num} занесены в таблицу')
            ExitFromAccount(driver)
            source.ACC_TO_CHANGE = None
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
