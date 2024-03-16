from Base import populate_db
from Class import CustomWord, CustomUser, CustomUserWord
import sqlalchemy as sq
from sqlalchemy.orm import sessionmaker

import random
from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup


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


def get_words(engine, user_custom_cid):
    session = sessionmaker(bind=engine)()
    user_words = session.query(CustomUserWord.custom_word, CustomUserWord.custom_translate) \
        .join(CustomUser, CustomUser.user_id == CustomUserWord.user_id) \
        .filter(CustomUser.custom_cid == user_custom_cid).all()
    all_words = session.query(CustomWord.custom_word, CustomWord.custom_translate).all()
    result = all_words + user_words
    session.close()
    return result


def add_words(engine, custom_cid, word, translate):
    session = sessionmaker(bind=engine)()
    user_id = session.query(CustomUser.user_id).filter(CustomUser.custom_cid == custom_cid).first()[0]
    new_word = CustomUserWord(custom_word=word, custom_translate=translate, user_id=user_id)
    session.add(new_word)
    session.commit()
    session.close()


def delete_words(engine, custom_cid, word):
    session = sessionmaker(bind=engine)()
    user_id = session.query(CustomUser.user_id).filter(CustomUser.custom_cid == custom_cid).first()[0]
    session.query(CustomUserWord).filter(CustomUserWord.user_id == user_id, CustomUserWord.custom_word == word).delete()
    session.commit()
    session.close()


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

    markup = create_cards_markup()

    bot.send_message(message.chat.id, "Your message", reply_markup=markup)


def create_cards_markup():
    markup = types.ReplyKeyboardMarkup(row_width=2)
    return markup


def get_target_word_from_db():
    pass
def get_translation_from_db(target_word):
    pass
def get_other_words_from_db():
    pass

global buttons
buttons = []
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

markup.add(*buttons)

greeting = f"Выбери перевод слова:\n🇷🇺 {translate}"
bot.send_message(message.chat.id, greeting, reply_markup=markup)
bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
    data['target_word'] = target_word
    data['translate_word'] = translate
    data['other_words'] = others

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



