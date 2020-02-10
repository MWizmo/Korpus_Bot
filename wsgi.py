import telebot
import bot_config
from db_commands import *
from sqlalchemy import func

bot = telebot.TeleBot(bot_config.token)


@bot.message_handler(commands=['start'])
def start(message):
    if isUserInDb(message.from_user.username):
        if not(checkBotRegistration(message.from_user.username, message.from_user.id, message.chat.id)):
            bot.send_message(message.chat.id,
                             "Для упрощения нашего взаимодействия через систему загрузите, пожалуйста, свою фотографию.")
            setState(message.from_user.id, 2)
        else:
            setState(message.from_user.id, 1)
            bot.send_message(message.chat.id,
                             "С возвращением!", reply_markup=getKeyboard(message.from_user.id))
    else:
        markup = InlineKeyboardMarkup()
        btn_my_site = InlineKeyboardButton(text='Регистрация', url='http://lk.korpus.io/')
        markup.add(btn_my_site)
        bot.send_message(message.chat.id,
                         """Кажется, ты еще не зарегистрирован в системе. Перейди по ссылке для регистрации, 
                         после чего возвращайся и вновь введи /start""",
                         reply_markup=markup)


@bot.message_handler(content_types=["photo"],
                     func=lambda message: getState(message.from_user.id) == 2)
def user_entering_pic(message):
    photo = message.photo[len(message.photo) - 1].file_id
    _id = message.from_user.id
    setPhoto(_id, photo)
    bot.send_photo(message.chat.id, photo)
    bot.send_message(message.chat.id, 'Добро пожаловать!', reply_markup=getKeyboard(message.from_user.id))
    setState(message.from_user.id, 1)


@bot.callback_query_handler(func=lambda call: True and call.data.startswith('set_rang'))
def setting_rang1(call):
    if call.data.split('%')[1] == 'back':
        # setState(call.from_user.id, 1)
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(call.message.chat.id, "Главное меню",
                         reply_markup=getKeyboard(call.from_user.id))
    else:
        _id = call.data.split('%')[1]
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.row(telebot.types.InlineKeyboardButton(text='Админ', callback_data='setting_rang#1#' + str(_id)),
                     telebot.types.InlineKeyboardButton(text='Атаман', callback_data='setting_rang#2#' + str(_id)))
        keyboard.row(telebot.types.InlineKeyboardButton(text='Курсант', callback_data='setting_rang#3#' + str(_id)),
                     telebot.types.InlineKeyboardButton(text='Курсант-тимлид',
                                                        callback_data='setting_rang#4#' + str(_id)))
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(call.message.chat.id,
                         'Выберите роль для пользователя ' + getName(_id) + ' (текущие роли: ' + getStatusTitleByID(_id) + ')',
                         reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: True and call.data.startswith('setting_rang'))
def setting_rang2(call):
    items = call.data.split('#')
    rang = items[1]
    _id = items[2]
    setStatusByID(_id, rang)
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    bot.send_message(call.message.chat.id, "Успешно",
                     reply_markup=getKeyboard(call.from_user.id))
    # bot.send_message(GetChatId(nick, cursor), 'Вам добавлена роль "'+GetTitleOfRang(rang, cursor)+'"')


@bot.callback_query_handler(func=lambda call: True and call.data.startswith('ask_teamleads'))
def set_teamleads(call):
    user_id = int(call.data.split('%')[1])
    if user_id == -1:
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(call.message.chat.id, "Успешно",
                         reply_markup=getKeyboard(call.from_user.id))
    else:
        setStatus(user_id, 4)


@bot.message_handler(func=lambda message: getState(message.from_user.id) == 10)
def enter_quest_message(message):
    if message.text == 'Отмена':
        bot.send_message(message.chat.id, 'Функции администратора', reply_markup=getAdminKeyboard())
        setState(message.from_user.id, 1)
    else:
        cadets = [user for user in User.query.all() if User.check_can_be_marked(user.id)]
        month = datetime.datetime.now().month
        for user in cadets:
            if len(Questionnaire.query.filter(Questionnaire.user_id == user.id,
                                              func.month(Questionnaire.date) == month).all()) < 2:
                if user.tg_id:
                    bot.send_message(user.chat_id, message.text)

        bot.send_message(message.chat.id, 'Успешно', reply_markup=getKeyboard(message.from_user.id))
        setState(message.from_user.id, 1)


@bot.callback_query_handler(func=lambda call: True and call.data.startswith('alert_voting'))
def choose_axis_for_alert(call):
    axis = int(call.data.split('_')[-1])
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    if axis == 4:
        bot.send_message(call.message.chat.id, 'Функции администратора', reply_markup=getAdminKeyboard())
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
        bot.send_message(call.message.chat.id,
                             'Еще не закончили оценку по оси отношений (* - не авторизован в боте):\n' +
                             '\n'.join(user_names) + '\n\nВведите сообщение', reply_markup=markup)
        setState(call.from_user.id, 11)
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
        bot.send_message(call.message.chat.id,
                             'Еще не закончили оценку по оси дела (* - не авторизован в боте):\n' +
                             '\n'.join(user_names) + '\n\nВведите сообщение', reply_markup=markup)
        setState(call.from_user.id, 12)
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
        bot.send_message(call.message.chat.id,
                             'Еще не закончили оценку по оси власти (* - не авторизован в боте):\n' +
                             '\n'.join(user_names) + '\n\nВведите сообщение', reply_markup=markup)
        setState(call.from_user.id, 13)


@bot.message_handler(func=lambda message: getState(message.from_user.id) == 11)
def enter_voting_relations_message(message):
    if message.text == 'Отмена':
        bot.send_message(message.chat.id, 'Функции администратора', reply_markup=getAdminKeyboard())
        setState(message.from_user.id, 1)
    else:
        users = [user for user in User.query.all() if User.check_top_cadet(user.id)]
        month = datetime.datetime.now().month
        marked_teams_num = len(Teams.query.filter_by(type=1).all())
        for user in users:
            if len(Voting.query.filter(Voting.user_id == user.id,
                                       func.month(Voting.date) == month, Voting.axis_id == 1).all()) < marked_teams_num:
                if user.tg_id:
                    bot.send_message(user.chat_id, message.text)
        bot.send_message(message.chat.id, 'Успешно', reply_markup=getKeyboard(message.from_user.id))
        setState(message.from_user.id, 1)


@bot.message_handler(func=lambda message: getState(message.from_user.id) == 12)
def enter_voting_business_message(message):
    if message.text == 'Отмена':
        bot.send_message(message.chat.id, 'Функции администратора', reply_markup=getAdminKeyboard())
        setState(message.from_user.id, 1)
    else:
        users = [user for user in User.query.all() if (User.check_expert(user.id) or User.check_tracker(user.id))]
        month = datetime.datetime.now().month
        marked_teams_num = len(Teams.query.filter_by(type=1).all())
        for user in users:
            if len(Voting.query.filter(Voting.user_id == user.id,
                                       func.month(Voting.date) == month, Voting.axis_id == 2).all()) < marked_teams_num:
                if user.tg_id:
                    bot.send_message(user.chat_id, message.text)
        bot.send_message(message.chat.id, 'Успешно', reply_markup=getKeyboard(message.from_user.id))
        setState(message.from_user.id, 1)


@bot.message_handler(func=lambda message: getState(message.from_user.id) == 13)
def enter_voting_authority_message(message):
    if message.text == 'Отмена':
        bot.send_message(message.chat.id, 'Функции администратора', reply_markup=getAdminKeyboard())
        setState(message.from_user.id, 1)
    else:
        users = [user for user in User.query.all() if User.check_chieftain(user.id)]
        month = datetime.datetime.now().month
        for user in users:
            if len(Voting.query.filter(Voting.user_id == user.id,
                                       func.month(Voting.date) == month, Voting.axis_id == 3).all()) < 1:
                if user.tg_id:
                    bot.send_message(user.chat_id, message.text)
        bot.send_message(message.chat.id, 'Успешно', reply_markup=getKeyboard(message.from_user.id))
        setState(message.from_user.id, 1)


@bot.message_handler(content_types=["text"])
def text(message):
    mess = message.text
    _id = message.from_user.id
    # if getState(_id) == -1:
    #     start(message)
    if mess == admin_func_btn and isAdmin(_id):
        bot.send_message(message.chat.id, 'Выберите действие', reply_markup=getAdminKeyboard())
    elif mess == back_btn:
        bot.send_message(message.chat.id, 'Главное меню', reply_markup=getKeyboard(_id))
    elif mess == choose_best_btn:
        users = getUsersForChoosingBest(_id)
        if users:
            pass
        else:
            bot.send_message(message.chat.id, 'В данный момент не из кого выбирать')
    elif mess == show_role_btn and isAdmin(_id):
        set_rang(message, bot)
    elif mess == alert_voting_btn and isAdmin(_id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text='Ось отношений', callback_data='alert_voting_1'))
        markup.add(InlineKeyboardButton(text='Ось дела', callback_data='alert_voting_2'))
        markup.add(InlineKeyboardButton(text='Ось власти', callback_data='alert_voting_3'))
        markup.add(InlineKeyboardButton(text='Отмена', callback_data='alert_voting_4'))
        bot.send_message(message.chat.id, 'Выберите ось', reply_markup=markup)
    elif mess == alert_form_btn and isAdmin(_id):
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
        bot.send_message(message.chat.id, 'Еще не заполнили анкеты (* - не авторизован в боте):\n' +
                         '\n'.join(user_names) + '\n\nВведите сообщение', reply_markup=markup)
        setState(message.from_user.id, 10)
    elif mess == ask_teamleads_btn and isAdmin(_id):
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
                bot.send_message(message.chat.id, 'Пользователь ' + ataman.login + ' еще не авторизовался в боте')
        bot.send_message(message.chat.id, 'Оповещения разосланы')
    elif mess == ask_teams_crew_btn:
        pass
    else:
        bot.send_message(message.chat.id, 'Неизвестная команда', reply_markup=getKeyboard(_id))


# bot.delete_webhook()
bot.polling(none_stop=True)
