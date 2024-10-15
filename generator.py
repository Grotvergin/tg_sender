from random import choice
from source import FAKER


def GenerateRandomRussianName() -> (str, str):
    first_names = ['Алексей', 'Андрей', 'Борис', 'Владимир', 'Георгий', 'Дмитрий', 'Евгений', 'Игорь', 'Константин', 'Максим']
    last_names = ['Иванов', 'Смирнов', 'Кузнецов', 'Попов', 'Соколов', 'Лебедев', 'Козлов', 'Новиков', 'Морозов', 'Петров']
    return choice(first_names), choice(last_names)


def GenerateRandomWord(min_length: int) -> str:
    word = FAKER.word()
    while len(word) < min_length:
        word += f's{FAKER.word()}'
    return word
