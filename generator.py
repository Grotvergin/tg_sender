from source import FAKER
from common import Stamp
from source import IMG_PATH, BOT
# ---
from random import choice
# ---
from io import BytesIO
from PIL import Image
from requests import get


def GenerateRandomRussianName() -> (str, str):
    first_names = ['Алексей', 'Андрей', 'Борис', 'Владимир', 'Георгий', 'Дмитрий', 'Евгений',
                   'Игорь', 'Константин', 'Максим', 'Николай', 'Олег', 'Павел', 'Роман', 'Сергей',
                   'Тимофей', 'Фёдор', 'Юрий', 'Ярослав']
    last_names = ['Иванов', 'Смирнов', 'Кузнецов', 'Попов', 'Соколов', 'Лебедев', 'Козлов', 'Новиков',
                  'Морозов', 'Петров', 'Волков', 'Соловьёв', 'Васильев', 'Зайцев', 'Павлов', 'Семёнов',
                  'Голубев', 'Виноградов', 'Богданов', 'Воробьёв', 'Фёдоров', 'Михайлов', 'Беляев']
    return choice(first_names), choice(last_names)


def GenerateRandomWord(min_length: int) -> str:
    word = FAKER.word()
    while len(word) < min_length:
        word += f's{FAKER.word()}'
    return word


def GenerateRandomDescription() -> str:
    descriptions = [
        'Люблю путешествовать и открывать новые места.',
        'Фанат спорта и здорового образа жизни.',
        'Веду блог о кулинарии и рецептах.',
        'Интересуюсь искусством и культурой.',
        'Занимаюсь фотографией и видеосъемкой.',
        'Люблю читать книги и смотреть фильмы.',
        'Играю на гитаре и пою.',
        'Учусь программированию и разработке.',
        'Веду активный образ жизни и занимаюсь спортом.',
        'Интересуюсь наукой и технологиями.',
        'Люблю общаться и заводить новых друзей.',
        'Путешествую по миру и изучаю культуры.',
        'Учусь новым навыкам и развиваюсь.',
        'Интересуюсь историей и географией.',
        'Люблю природу и активный отдых.',
        'Фанат музыки и посещения концертов.',
        'Играю в видеоигры и смотрю стримы.',
        'Занимаюсь рисованием и дизайном.',
        'Люблю путешествовать и открывать новые места.',
        'Фанат спорта и здорового образа жизни.',
        'Веду блог о кулинарии и рецептах.',
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
