import source
from source import BOT, IMG_PATH, CANCEL_BTN
from common import Stamp, ShowButtons
from random import choice
from requests import get
from PIL import Image
from io import BytesIO
from os import remove
from os.path import split
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.sync import TelegramClient
from telethon.tl.types import InputPhoneContact
from telethon.tl.functions.photos import UploadProfilePhotoRequest
from telethon.tl.functions.contacts import ImportContactsRequest
from random import randint
from telebot.types import Message
from asyncio import sleep as async_sleep
from telethon.tl.types import (InputPrivacyValueDisallowAll,
                               InputPrivacyKeyPhoneNumber,
                               InputPrivacyKeyPhoneCall,
                               InputPrivacyKeyChatInvite,
                               InputPrivacyKeyStatusTimestamp)
from telethon.tl.functions.account import SetPrivacyRequest


# TODO Wrong cancellation
def RequestChangeProfile(message: Message) -> None:
    if message.text == CANCEL_BTN[0]:
        ShowButtons(message, source.WELCOME_BTNS, '❔ Выберите действие:')
        return
    try:
        num = int(message.text)
    except ValueError:
        Stamp(f'Failed to convert {message.text} to number, retrying', 'e')
        ShowButtons(message, CANCEL_BTN, '❌ Введите только цифры номера телефона, '
                                               'например, 74951234567')
        BOT.register_next_step_handler(message, RequestChangeProfile)
    else:
        acc = FindAccountByNumber(num)
        if not acc:
            Stamp(f'User {message.from_user.id} requested to change profile for {num}, but not found', 'w')
            ShowButtons(message, CANCEL_BTN, '❌ Номер телефона не найден, попробуйте еще раз')
            BOT.register_next_step_handler(message, RequestChangeProfile)
            return
        source.ACC_TO_CHANGE = acc
        source.WARDEN_CHAT_ID = message.from_user.id
        Stamp(f'User {message.from_user.id} requested to change profile for {num}', 'i')
        BOT.send_message(message.from_user.id, '🔄 Изменение профиля начато')


async def CheckProfileChange() -> None:
    while True:
        if source.ACC_TO_CHANGE:
            await SetProfileInfo(source.ACC_TO_CHANGE, source.WARDEN_CHAT_ID)
            await SetProfilePicture(source.ACC_TO_CHANGE, source.WARDEN_CHAT_ID)
            await AddContacts(source.ACC_TO_CHANGE, 50, source.WARDEN_CHAT_ID)
            await UpdatePrivacySettings(source.ACC_TO_CHANGE, source.WARDEN_CHAT_ID)
            source.ACC_TO_CHANGE = None
        await async_sleep(source.SHORT_SLEEP)


def FindAccountByNumber(num: int) -> TelegramClient | None:
    for acc in source.ACCOUNTS:
        if int(split(acc.session.filename)[-1][:-8]) == num:
            return acc
    return None


def GenerateRandomRussianName() -> (str, str):
    first_names = ['Алексей', 'Андрей', 'Борис', 'Владимир', 'Георгий', 'Дмитрий', 'Евгений', 'Игорь', 'Константин', 'Максим']
    last_names = ['Иванов', 'Смирнов', 'Кузнецов', 'Попов', 'Соколов', 'Лебедев', 'Козлов', 'Новиков', 'Морозов', 'Петров']
    return choice(first_names), choice(last_names)


def GenerateRandomDescription() -> str:
    descriptions = [
        'Люблю путешествовать и открывать новые места.',
        'Фанат спорта и здорового образа жизни.',
        'Веду блог о кулинарии и рецептах.',
        'Интересуюсь искусством и культурой.',
        'Занимаюсь фотографией и видеосъемкой.'
    ]
    return choice(descriptions)


def GetRandomProfilePicture(user_id: int) -> None:
    Stamp('Getting random profile picture', 'i')
    try:
        response = get('https://picsum.photos/400')
    except ConnectionError as e:
        BOT.send_message(user_id, f'❌ Ошибка при получении случайного изображения')
        Stamp(f'Failed to get random image: {e}', 'e')
    else:
        Stamp('Saving random profile picture', 'i')
        img = Image.open(BytesIO(response.content))
        img.save(IMG_PATH)


# TODO Uncomment after testing
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
