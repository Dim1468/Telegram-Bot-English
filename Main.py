from Base import populate_db
from Class import CustomWord, CustomUser, CustomUserWord
import sqlalchemy as sq
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import logging

import random
from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup

logging.basicConfig(filename='errors.log', level=logging.ERROR)

def user_list(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    users = session.query(CustomUser).all()
    user_ids = [user.cid for user in users]
    session.close()
    return user_ids


def add_users(engine, user_id):
    session = sessionmaker(bind=engine)()
    session.add(CustomUser(custom_cid=user_id))  # Заменил "cid" на "custom_cid" как в классе
    session.commit()
    session.close()


def add_word(engine, custom_cid, word, translate):
    try:
        Session = sessionmaker(bind=engine)
        with Session() as session:
            user = session.query(CustomUser).filter(CustomUser.custom_cid == custom_cid).first()
            if user:
                user_id = user.user_id
                new_word = CustomUserWord(custom_word=word, custom_translate=translate, user_id=user_id)
                session.add(new_word)
                session.commit()
                return True  # Успешно добавлено слово
            else:
                logging.error("Пользователь с custom_cid={} не найден.".format(custom_cid))
                return False  # Пользователь не найден
    except sq.SomeException as e:
        logging.error("Ошибка при добавлении слова: %s", e)
        return False  # Ошибка при добавлении слова

def delete_word(engine, custom_cid, word, sqlalchemy=None):
    try:
        Session = sessionmaker(bind=engine)
        with Session() as session:
            user = session.query(CustomUser).filter(CustomUser.custom_cid == custom_cid).first()
            if user:
                user_id = user.user_id
                word_to_delete = session.query(CustomUserWord).filter(CustomUserWord.user_id == user_id,
                                                                      CustomUserWord.custom_word == word).first()
                if word_to_delete:
                    session.delete(word_to_delete)
                    session.commit()
                    return True  # Успешно удалено слово
                else:
                    print("Слово '{}' не найдено для пользователя с custom_cid={}".format(word, custom_cid))
                    return False  # Слово не найдено
            else:
                print("Пользователь с custom_cid={} не найден.".format(custom_cid))
                return False  # Пользователь не найден
    except sqlalchemy as e:
        print("Ошибка при удалении слова:", e)
        return False  # Ошибка при удалении слова


engine = sq.create_engine('postgresql://postgres:password@localhost:5432/tgbot')
Session = sessionmaker(bind=engine)
session = Session()
populate_db(engine)
print('Start telegram bot...')

state_storage = StateMemoryStorage()
token_bot = 'bot'
bot = TeleBot(token_bot, state_storage=state_storage)

known_users = user_list(engine)
print(f'Добавлено {len(known_users)} пользователей')
userStep = {}
buttons = []

def show_hint(*lines):
    return '\n'.join(lines)

def show_target(data):
    return f"{data['target_word']} -> {data['translate_word']}"

class Command:
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово🔙'
    NEXT = 'Дальше ⏭'


class MyStates(StatesGroup):
    target_word = State()
    translate_word = State()
    another_words = State()


def get_user_step(uid):
    if uid in userStep:
        return userStep[uid]
    else:
        known_users.append(uid)
        userStep[uid] = 0
        print("New user detected, who hasn't used \"/start\" yet")
        return 0
Hello_text = '''Привет
  Начнем изучать  английский язык.
    Есть возможность использовать тренажёр, как пазл, и собирать свою собственную базу для обучения.
  Для этого воспрользуйся инструментами:
  - добавить слово ➕,
  - удалить слово 🔙.
   Начнём ⬇️?'''

@bot.message_handler(commands=['cards', 'start'])
def create_cards(message):
    cid = message.chat.id
    if cid not in known_users:
        known_users.append(cid)
        add_users(engine, cid)
        userStep[cid] = 0
        bot.send_message(cid, Hello_text)

    markup = create_cards_markup()  # Создание разметки с карточками

    bot.send_message(message.chat.id, "Your message", reply_markup=markup)

def create_cards_markup():
    markup = types.ReplyKeyboardMarkup(row_width=2)
    card1 = types.KeyboardButton("Card 1")
    card2 = types.KeyboardButton("Card 2")
    card3 = types.KeyboardButton("Card 3")
    markup.add(card1, card2, card3)  # Добавление карточек к разметке
    return markup


def get_target_word_from_db():
    Session = sessionmaker(bind=engine)
    session = Session()
    target_word = session.query(CustomWord.custom_word).first()
    session.close()
    return target_word

def get_translation_from_db(target_word):
    Session = sessionmaker(bind=engine)
    session = Session()
    translation = session.query(CustomWord.custom_translate).filter_by(custom_word=target_word).first()
    session.close()
    return translation

def get_other_words_from_db():
    Session = sessionmaker(bind=engine)
    session = Session()
    other_words = session.query(CustomWord.custom_word).filter(CustomWord.custom_word != target_word).all()
    session.close()
    return other_words


buttons = []

markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
markup.add(types.KeyboardButton(text="Назад в меню"))

target_word = get_target_word_from_db()
translate = get_translation_from_db(target_word)
others = get_other_words_from_db()

target_word_btn = types.KeyboardButton(target_word)
buttons.append(target_word_btn)

other_words_btns = [types.KeyboardButton(word) for word in others]
buttons.extend(other_words_btns)

random.shuffle(buttons)

next_btn = types.KeyboardButton(Command.NEXT)
add_word_btn = types.KeyboardButton(Command.ADD_WORD)
delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
buttons.extend([next_btn, add_word_btn, delete_word_btn])



@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_cards(message):
    create_cards(message)

@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        print(data['target_word'])  # удалить из БД

@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word(message):
    cid = message.chat.id
    userStep[cid] = 1
    print(message.text)  # сохранить в БД


@bot.message_handler(func=lambda message: True, content_types=['text'])

def message_reply(message):
    text = message.text
    markup = types.ReplyKeyboardMarkup(row_width=2)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        target_word = data['target_word']
        if text == target_word:
            hint = show_target(data)
            hint_text = ["Отлично!❤", hint]
            next_btn = types.KeyboardButton(Command.NEXT)
            add_word_btn = types.KeyboardButton(Command.ADD_WORD)
            delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
            buttons.extend([next_btn, add_word_btn, delete_word_btn])
            hint = show_hint(*hint_text)
        else:
            for btn in buttons:
                if btn.text == text:
                    btn.text = text + '❌'
                    break
            hint = show_hint("Допущена ошибка!",
                             f"Попробуй ещё раз вспомнить слово 🇷🇺{data['translate_word']}")
    markup.add(*buttons)
    bot.send_message(message.chat.id, hint, reply_markup=markup)


bot.add_custom_filter(custom_filters.StateFilter(bot))

bot.infinity_polling(skip_pending=True)