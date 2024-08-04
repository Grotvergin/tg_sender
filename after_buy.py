from source import (BOT, IMG_PATH)
from common import Stamp
from random import choice
from requests import get
from PIL import Image
from io import BytesIO
from os import remove
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.sync import TelegramClient
from telethon.tl.types import InputPhoneContact
from telethon.tl.functions.photos import UploadProfilePhotoRequest
from telethon.tl.functions.contacts import ImportContactsRequest
from random import randint


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


def GetRandomProfilePicture(user_id: int) -> str | None:
    try:
        response = get('https://picsum.photos/400')
    except ConnectionError as e:
        BOT.send_message(user_id, f'❌ Ошибка при получении случайного изображения')
        Stamp(f'Failed to get random image: {e}', 'e')
        return None
    else:
        img = Image.open(BytesIO(response.content))
        img.save(IMG_PATH)
        return IMG_PATH


async def SetProfilePicture(client: TelegramClient, user_id: int) -> None:
    Stamp('Setting profile picture', 'i')
    BOT.send_message(user_id, '🖼 Изменяю фотографию профиля...')
    file = await client.upload_file(IMG_PATH)
    await client(UploadProfilePhotoRequest(file))
    remove(IMG_PATH)


async def SetProfileInfo(client: TelegramClient, user_id: int) -> None:
    Stamp('Setting profile info', 'i')
    BOT.send_message(user_id, '📝 Изменяю информацию профиля...')
    first_name, last_name = GenerateRandomRussianName()
    about = GenerateRandomDescription()
    await client(UpdateProfileRequest(first_name=first_name,
                                      last_name=last_name,
                                      about=about))


async def AddContacts(client: TelegramClient, num: int, user_id: int) -> None:
    Stamp(f'Adding {num} contacts', 'i')
    BOT.send_message(user_id, f'📞 Добавляю {num} контактов...')
    contacts = []
    for _ in range(num):
        first_name, last_name = GenerateRandomRussianName()
        phone = f'+{randint(1, 99)}{randint(1000000000, 9999999999)}'
        contact = InputPhoneContact(client_id=randint(0, 999999),
                                    phone=phone,
                                    first_name=first_name,
                                    last_name=last_name)
        contacts.append(contact)
    await client(ImportContactsRequest(contacts))
