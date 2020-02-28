from app import bot, app
import bot_config
from db_commands import *
from sqlalchemy import func
from flask import request, blueprints
import requests


blueprint = blueprints.Blueprint('blueprint', __name__)


@blueprint.route('/tg', methods=['POST'])
def answer_telegram():
    update = request.get_json()
    if 'message' in update:
        message = update.get('message')
        if message.get('text'):
            process_text(message)
        elif message.get('photo'):
            process_image(message)
        else:
            print(message)
    elif 'callback_query' in update:
        callback = update.get('callback_query')
        process_callback(callback)
    else:
        print(update)
    return "Message Processed"


def process_text(message):
    text = message['text']
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    if text == '/start':
        start(message)
    if getState(user_id) == -1:
        start(message)
    state = getState(user_id)
    if state == 1:
        if text == admin_func_btn and isAdmin(user_id):
            bot.send_message(chat_id, 'Выберите действие', reply_markup=getAdminKeyboard())
        elif text == back_btn:
            bot.send_message(chat_id, 'Главное меню', reply_markup=getKeyboard(user_id))
        elif text == alert_voting_btn and isAdmin(user_id):
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(text='Ось отношений', callback_data='alert_voting_1'))
            markup.add(InlineKeyboardButton(text='Ось дела', callback_data='alert_voting_2'))
            markup.add(InlineKeyboardButton(text='Ось власти', callback_data='alert_voting_3'))
            markup.add(InlineKeyboardButton(text='Отмена', callback_data='alert_voting_4'))
            bot.send_message(chat_id, 'Выберите ось', reply_markup=markup)
        elif text == alert_form_btn and isAdmin(user_id):
            cadets = [user for user in User.query.all() if User.check_can_be_marked(user.id)]
            user_names = list()
            month = datetime.datetime.now().month
            for user in cadets:
                if len(Questionnaire.query.filter(Questionnaire.user_id == user.id,
                                                  func.month(Questionnaire.date) == month).all()) < 2:
                    if user.tg_id:
                        user_names.append('{} {}'.format(user.name, user.surname))
                    else:
                        user_names.append('{} {}*'.format(user.name, user.surname))
            markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            markup.add('Отмена')
            bot.send_message(chat_id, 'Еще не заполнили анкеты (* - не авторизован в боте):\n' +
                             '\n'.join(user_names) + '\n\nВведите сообщение', reply_markup=markup)
            setState(user_id, 10)
        elif text == ask_teamleads_btn and isAdmin(user_id):
            users = User.query.all()
            markup = InlineKeyboardMarkup()
            for user in users:
                markup.add(InlineKeyboardButton(text=user.login, callback_data="ask_teamleads%" + str(user.id)))
            markup.add(InlineKeyboardButton(text='<Закончить>', callback_data="ask_teamleads%0"))
            atamans = User.query.filter_by(status=2).all()
            for ataman in atamans:
                if ataman.chat_id:
                    bot.send_message(ataman.chat_id, """Выберите из списка курсантов тех,
                        кто является тимлидом в каком-либо проекте""", reply_markup=markup)
                else:
                    bot.send_message(chat_id, 'Пользователь ' + ataman.login + ' еще не авторизовался в боте')
            bot.send_message(chat_id, 'Оповещения разосланы')
        elif text == ask_teams_crew_btn:
            pass
        # else:
        #     bot.send_message(chat_id, 'Неизвестная команда', reply_markup=getKeyboard(user_id))
    elif state == 10:
        if text == 'Отмена':
            bot.send_message(chat_id, 'Функции администратора', reply_markup=getAdminKeyboard())
            setState(user_id, 1)
        else:
            cadets = [user for user in User.query.all() if User.check_can_be_marked(user.id)]
            month = datetime.datetime.now().month
            for user in cadets:
                if len(Questionnaire.query.filter(Questionnaire.user_id == user.id,
                                                  func.month(Questionnaire.date) == month).all()) < 2:
                    if user.tg_id:
                        bot.send_message(user.chat_id, text)

            bot.send_message(chat_id, 'Успешно', reply_markup=getKeyboard(user_id))
            setState(user_id, 1)
    elif state == 11:
        if text == 'Отмена':
            bot.send_message(chat_id, 'Функции администратора', reply_markup=getAdminKeyboard())
            setState(user_id, 1)
        else:
            users = [user for user in User.query.all() if User.check_top_cadet(user.id)]
            month = datetime.datetime.now().month
            marked_teams_num = len(Teams.query.filter_by(type=1).all())
            for user in users:
                if len(Voting.query.filter(Voting.user_id == user.id,
                                           func.month(Voting.date) == month, Voting.axis_id == 1).all()) < marked_teams_num:
                    if user.tg_id:
                        bot.send_message(user.chat_id, text)
            bot.send_message(chat_id, 'Успешно', reply_markup=getKeyboard(user_id))
            setState(user_id, 1)
    elif state == 12:
        if text == 'Отмена':
            bot.send_message(chat_id, 'Функции администратора', reply_markup=getAdminKeyboard())
            setState(user_id, 1)
        else:
            users = [user for user in User.query.all() if (User.check_expert(user.id) or User.check_tracker(user.id))]
            month = datetime.datetime.now().month
            marked_teams_num = len(Teams.query.filter_by(type=1).all())
            for user in users:
                if len(Voting.query.filter(Voting.user_id == user.id,
                                           func.month(Voting.date) == month, Voting.axis_id == 2).all()) < marked_teams_num:
                    if user.tg_id:
                        bot.send_message(user.chat_id, text)
            bot.send_message(chat_id, 'Успешно', reply_markup=getKeyboard(user_id))
            setState(user_id, 1)
    elif state == 13:
        if text == 'Отмена':
            bot.send_message(chat_id, 'Функции администратора', reply_markup=getAdminKeyboard())
            setState(user_id, 1)
        else:
            users = [user for user in User.query.all() if User.check_chieftain(user.id)]
            month = datetime.datetime.now().month
            for user in users:
                if len(Voting.query.filter(Voting.user_id == user.id,
                                           func.month(Voting.date) == month, Voting.axis_id == 3).all()) < 1:
                    if user.tg_id:
                        bot.send_message(user.chat_id, text)
            bot.send_message(chat_id, 'Успешно', reply_markup=getKeyboard(user_id))
            setState(user_id, 1)


def process_image(message):
    if getState(message['from']['id']) == 2:
        photo = message['photo'][len(message['photo']) - 1]['file_id']
        _id = message['from']['id']
        photo_url = 'https://api.telegram.org/file/bot' + bot_config.token + '/' + bot.get_file(photo).file_path
        f = open(app.root_path + '/user_photos/user' + str(get_id(message['from']['id'])) + '.jpg', "wb")
        ufr = requests.get(photo_url)
        f.write(ufr.content)
        f.close()
        setPhoto(_id, photo_url)
        # bot.send_photo(message['chat']['id'], photo)
        bot.send_message(message['chat']['id'], 'Добро пожаловать!', reply_markup=getKeyboard(message['from']['id']))
        setState(message['from']['id'], 1)


def process_callback(callback):
    data = callback['data']
    user_id = callback['from']['id']
    message_id = callback['message']['message_id']
    chat_id = callback['message']['chat']['id']
    if data.startswith('alert_voting'):
        axis = int(data.split('_')[-1])
        bot.delete_message(chat_id=chat_id, message_id=message_id)
        if axis == 4:
            bot.send_message(chat_id, 'Функции администратора', reply_markup=getAdminKeyboard())
        elif axis == 1:
            users = [user for user in User.query.all() if User.check_top_cadet(user.id)]
            user_names = list()
            month = datetime.datetime.now().month
            marked_teams_num = len(Teams.query.filter_by(type=1).all())
            for user in users:
                if len(Voting.query.filter(Voting.user_id == user.id,
                                           func.month(Voting.date) == month, Voting.axis_id == 1).all()) < marked_teams_num:
                    if user.tg_id:
                        user_names.append('{} {}'.format(user.name, user.surname))
                    else:
                        user_names.append('{} {}*'.format(user.name, user.surname))
            markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            markup.add('Отмена')
            bot.send_message(chat_id,
                                 'Еще не закончили оценку по оси отношений (* - не авторизован в боте):\n' +
                                 '\n'.join(user_names) + '\n\nВведите сообщение', reply_markup=markup)
            setState(user_id, 11)
        elif axis == 2:
            users = [user for user in User.query.all() if (User.check_expert(user.id) or User.check_tracker(user.id))]
            user_names = list()
            month = datetime.datetime.now().month
            marked_teams_num = len(Teams.query.filter_by(type=1).all())
            for user in users:
                if len(Voting.query.filter(Voting.user_id == user.id,
                                           func.month(Voting.date) == month, Voting.axis_id == 2).all()) < marked_teams_num:
                    if user.tg_id:
                        user_names.append('{} {}'.format(user.name, user.surname))
                    else:
                        user_names.append('{} {}*'.format(user.name, user.surname))
            markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            markup.add('Отмена')
            bot.send_message(chat_id,
                                 'Еще не закончили оценку по оси дела (* - не авторизован в боте):\n' +
                                 '\n'.join(user_names) + '\n\nВведите сообщение', reply_markup=markup)
            setState(user_id, 12)
        elif axis == 3:
            users = [user for user in User.query.all() if User.check_chieftain(user.id)]
            user_names = list()
            month = datetime.datetime.now().month
            for user in users:
                if len(Voting.query.filter(Voting.user_id == user.id,
                                           func.month(Voting.date) == month, Voting.axis_id == 3).all()) < 1:
                    if user.tg_id:
                        user_names.append('{} {}'.format(user.name, user.surname))
                    else:
                        user_names.append('{} {}*'.format(user.name, user.surname))
            markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            markup.add('Отмена')
            bot.send_message(chat_id,
                                 'Еще не закончили оценку по оси власти (* - не авторизован в боте):\n' +
                                 '\n'.join(user_names) + '\n\nВведите сообщение', reply_markup=markup)
            setState(user_id, 13)


def start(message):
    if isUserInDb(message['from']['username']):
        if not(checkBotRegistration(message['from']['username'], message['from']['id'], message['chat']['id'])):
            bot.send_message(message['chat']['id'],
                             "Для упрощения нашего взаимодействия через систему загрузите, пожалуйста, свою фотографию.")
            setState(message['from']['id'], 2)
        else:
            setState(message['from']['id'], 1)
            bot.send_message(message['chat']['id'],
                             "С возвращением!", reply_markup=getKeyboard(message['from']['id']))
    else:
        markup = InlineKeyboardMarkup()
        btn_my_site = InlineKeyboardButton(text='Регистрация', url='http://lk.korpus.io/')
        markup.add(btn_my_site)
        bot.send_message(message['chat']['id'],
                         """Кажется, ты еще не зарегистрирован в системе. Перейди по ссылке для регистрации,
                         после чего возвращайся и вновь введи /start""",
                         reply_markup=markup)

