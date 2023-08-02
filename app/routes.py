from app import bot, in_memory_storage
import bot_config
from db_commands import *
from sqlalchemy import func
from flask import request, blueprints
from eth_account import Account
import requests
from telebot.apihelper import ApiException

blueprint = blueprints.Blueprint('blueprint', __name__)


@blueprint.route('/ping', methods=['POST'])
def ping_user():
    try:
        user_id = int(request.form.get('user_id'))
        user = User.query.get(user_id)
        bot.send_message(user.chat_id, 'Проверка связи')
        return "Message Processed"
    except Exception as e:
        print(e)
        return str(e)


@blueprint.route('/promocode', methods=['POST'])
def promocode():
    user_id = int(request.form.get('user_id'))
    code = request.form.get('code')
    user = User.query.get(user_id)
    print(f'User {user_id}, chat_id {user.chat_id}, code {code}')
    bot.send_message(user.chat_id, 'Ваш промокод: ' + code)
    return "Message Processed"


@blueprint.route('/weekly_remind', methods=['POST'])
def weekly_remind():
    users = User.query.all()
    for user in users:
        try:
            status = getStatus(user.tg_id)
            if 2 in status or 4 in status or 5 in status:
                keyboard = InlineKeyboardMarkup()
                keyboard.add(InlineKeyboardButton(text="Ссылка на трекшен",
                                                  url="https://us02web.zoom.us/j/6012018339?pwd=SUx3V0FiT1RaM3ZJOGQvbHhXZ1ArUT09"))
                bot.send_message(user.chat_id, 'Привет! Сегодня оцениваем какие-то команды?', reply_markup=keyboard)
        except ApiException as e:
            print(f"Exception for user with id {user.id}: {str(e)}")


@blueprint.route('/send_weekly_results', methods=['POST'])
def send_weekly_results():
    r = requests.get('http://lk.korpus.io/send_results_of_weekly_voting')
    results = r.json()
    for team in results['results']:
        #if team['team_id'] == 18:
            for user in team['marks']:
                mess = f'''Сегодня проходила еженедельная оценка.\nВ рамках этой оценки вы получили следующие баллы:\n<b>{team["team"]}</b>\nДвижение - {team["marks"][user]["marks1"][0]}\nЗавершённость - {team["marks"][user]["marks2"][0]}\nПодтверждение средой - {team["marks"][user]["marks3"][0]}'''
                user = User.query.get(team["marks"][user]['user_id'])
                keyboard = InlineKeyboardMarkup()
                keyboard.add(InlineKeyboardButton('Детали', callback_data=f"details_{team['team_id']}_{results['date']}_{user.id}"))
                #if user.chat_id == '364905251':
                try:
                    bot.send_message(int(user.chat_id), mess, parse_mode='HTML', reply_markup=keyboard)
                except Exception as e:
                    print(e)
                    print(f'User {user.id}')
    return "Message Processed"


@blueprint.route('/tg', methods=['POST'])
def answer_telegram():
    try:
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
    except Exception as e:
        print(e)
    finally:
        return "Message Processed"


def process_text(message):
    text = message['text']
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    if text == '/start':
        start(message)
    elif getState(user_id) == -1:
        start(message)
    state = getState(user_id)
    if state == 1:
        if text == admin_func_btn and isAdmin(user_id):
            bot.send_message(chat_id, 'Выберите действие', reply_markup=getAdminKeyboard())
        elif text == back_btn:
            bot.send_message(chat_id, 'Главное меню', reply_markup=getKeyboard(user_id))
        elif text == alert_results_btn and isAdmin(user_id):
            setState(user_id, 101)
            keyboard = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            keyboard.add('Да')
            keyboard.add(back_btn)
            bot.send_message(chat_id, 'Разослать всем участвующим в оценке предварительные результаты?', reply_markup=keyboard)
        elif text == weekly_vote_btn:
            users = User.query.all()
            for user in users:
                try:
                    status = getStatus(user.tg_id)
                    if 2 in status or 4 in status or 5 in status:
                        keyboard = InlineKeyboardMarkup()
                        keyboard.add(InlineKeyboardButton(text="Ссылка на трекшен", url="https://us02web.zoom.us/j/87112498599?pwd=WFdZZnZKQldiWmxGRklUVmwrQUowZz09"))
                        bot.send_message(user.chat_id, 'Привет! Сегодня оцениваем какие-то команды?', reply_markup=keyboard)
                except:
                    pass
            bot.send_message(chat_id, 'Оповещения отправлены')
        elif text == voting_btn and (isAdmin(user_id) or isTeamLead(user_id) or isTracker(user_id) or isChief(user_id)):
            today = datetime.date(datetime.datetime.now().year, datetime.datetime.now().month,
                                  datetime.datetime.now().day)
            teams = Teams.query.filter_by(type=1).all() + Teams.query.filter_by(type=4).all()
            markup = InlineKeyboardMarkup()
            for t in teams:
                wm = WeeklyVoting.query.filter(WeeklyVoting.user_id == get_id(user_id), WeeklyVoting.team_id == t.id,
                                               WeeklyVoting.finished == 1, WeeklyVoting.date == today).first()
                if not wm:
                    markup.add(InlineKeyboardButton(text=t.name, callback_data='choose_team_{}'.format(t.id)))
            markup.add(InlineKeyboardButton(text='<Назад>', callback_data='choose_team_0'))
            bot.send_message(chat_id, 'Выберите команду для оценки', reply_markup=markup)
        elif text == alert_voting_btn and isAdmin(user_id):
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(text='Ось отношений', callback_data='alert_voting_1'))
            markup.add(InlineKeyboardButton(text='Ось дела', callback_data='alert_voting_2'))
            markup.add(InlineKeyboardButton(text='Ось власти', callback_data='alert_voting_3'))
            markup.add(InlineKeyboardButton(text='Отмена', callback_data='alert_voting_4'))
            bot.send_message(chat_id, 'Выберите ось', reply_markup=markup)
        elif text == weekly_vote_members and isTeamLead(user_id):
            cadet_id = get_id(user_id)
            teams = Membership.query.filter_by(user_id=cadet_id).all()
            my_teams = []
            for t in teams:
                if TeamRoles.query.filter(TeamRoles.team_id == t.team_id, TeamRoles.user_id == cadet_id,
                                          TeamRoles.role_id == 1).first():
                    my_teams.append(t)
            my_teams_ids = [t.team_id for t in my_teams if Teams.query.filter_by(id=t.team_id).first().type in [1, 4]]
            if len(my_teams_ids) == 1:
                team = get_cadets_for_choosing(my_teams_ids[0], user_id)
                markup = InlineKeyboardMarkup()
                for cadet in team:
                    markup.add(InlineKeyboardButton(text=cadet[1],
                                                    callback_data='choose_members_for_wv_{}_{}'.format(my_teams_ids[0],
                                                                                                       cadet[0])))
                markup.add(InlineKeyboardButton(text='<Закончить выбор>',
                                                callback_data='choose_members_for_wv_0_0'))
                markup.add(InlineKeyboardButton(text='<Назад>', callback_data='choose_members_for_wv_0_0'))
                bot.send_message(chat_id, 'Выберите участников команды, которые получат баллы за текущую оценку',
                                 reply_markup=markup)
            else:
                markup = InlineKeyboardMarkup()
                for t_id in my_teams_ids:
                    team = Teams.query.get(t_id)
                    markup.add(InlineKeyboardButton(text=team.name, callback_data=f'choose_team_for_wv_{t_id}'))
                markup.add(InlineKeyboardButton(text='<Назад>', callback_data=f'choose_team_for_wv_0'))
                bot.send_message(chat_id,
                                 'Выберите команду для указания участников, которые получат баллы за текущую оценку',
                                 reply_markup=markup)
        # elif text == weekly_vote_members and isTeamLead(user_id):
        #     cadet_id = get_id(user_id)
        #     teams = Membership.query.filter_by(user_id=cadet_id).all()
        #     tid = [t.team_id for t in teams if Teams.query.filter_by(id=t.team_id).first().type in [1, 4]][0]
        #     team = get_cadets_for_choosing(tid, user_id)
        #     markup = InlineKeyboardMarkup()
        #     for cadet in team:
        #         markup.add(InlineKeyboardButton(text=cadet[1],
        #                                         callback_data='choose_members_for_wv_{}_{}'.format(tid, cadet[0])))
        #     markup.add(InlineKeyboardButton(text='<Закончить выбор>',
        #                                     callback_data='choose_members_for_wv_0_0'))
        #     #markup.add(InlineKeyboardButton(text='<Назад>', callback_data='choose_members_for_wv_0_0'))
        #     bot.send_message(chat_id, 'Выберите участников команды, которые получат баллы за текущую оценку',
        #                      reply_markup=markup)
        elif text == alert_form_btn and isAdmin(user_id):
            cadets = [user for user in User.query.all() if User.check_can_be_marked(user.id)]
            user_names = list()
            month = datetime.datetime.now().month
            for user in cadets:
                if len(Questionnaire.query.filter(Questionnaire.user_id == user.id,
                                                  func.month(Questionnaire.date) == month).all()) + len(
                    Questionnaire.query.filter(Questionnaire.user_id == user.id,
                                               func.month(Questionnaire.date) == month - 1).all()) < 1:
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
        else:
            bot.send_message(chat_id, 'Неизвестная команда', reply_markup=getKeyboard(user_id))
    elif state == 10:
        if text == 'Отмена':
            bot.send_message(chat_id, 'Функции администратора', reply_markup=getAdminKeyboard())
            setState(user_id, 1)
        else:
            cadets = [user for user in User.query.all() if User.check_can_be_marked(user.id)]
            month = datetime.datetime.now().month
            for user in cadets:
                if len(Questionnaire.query.filter(Questionnaire.user_id == user.id,
                                                  func.month(Questionnaire.date) == month).all()) < 1:
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
            error_users = []
            for user in users:
                try:
                    if len(Voting.query.filter(Voting.user_id == user.id,
                                               func.month(Voting.date) == month,
                                               Voting.axis_id == 1).all()) < marked_teams_num:
                        if user.tg_id:
                            bot.send_message(user.chat_id, text)
                except Exception as e:
                    error_users.append(User.get_full_name(user.id))
                    print("-- Alert Relations axis: ", e)
            error_text = '' if len(error_users) == 0 else '\nСообщения следующим пользователям не доставлены (см. логи): ' + ', '.join(error_users)
            bot.send_message(chat_id, 'Успешно' + error_text, reply_markup=getKeyboard(user_id))
            setState(user_id, 1)
    elif state == 12:
        if text == 'Отмена':
            bot.send_message(chat_id, 'Функции администратора', reply_markup=getAdminKeyboard())
            setState(user_id, 1)
        else:
            users = [user for user in User.query.all() if (User.check_expert(user.id) or User.check_tracker(user.id) or
                                                           User.check_teamlead(user.id))]
            month = datetime.datetime.now().month
            marked_teams_num = len(Teams.query.filter_by(type=1).all())
            error_users = []
            for user in users:
                try:
                    if len(Voting.query.filter(Voting.user_id == user.id,
                                               func.month(Voting.date) == month,
                                               Voting.axis_id == 2).all()) < marked_teams_num:
                        if user.tg_id:
                            bot.send_message(user.chat_id, text)
                except Exception as e:
                    error_users.append(User.get_full_name(user.id))
                    print("-- Alert Business axis: ", e)
            error_text = '' if len(
                error_users) == 0 else '\nСообщения следующим пользователям не доставлены (см. логи): ' + ', '.join(
                error_users)
            bot.send_message(chat_id, 'Успешно' + error_text, reply_markup=getKeyboard(user_id))
            setState(user_id, 1)
    elif state == 13:
        if text == 'Отмена':
            bot.send_message(chat_id, 'Функции администратора', reply_markup=getAdminKeyboard())
            setState(user_id, 1)
        else:
            users = [user for user in User.query.all() if User.check_chieftain(user.id)]
            month = datetime.datetime.now().month
            error_users = []
            for user in users:
                try:
                    if len(Voting.query.filter(Voting.user_id == user.id,
                                               func.month(Voting.date) == month, Voting.axis_id == 3).all()) < 1:
                        if user.tg_id:
                            bot.send_message(user.chat_id, text)
                except Exception as e:
                    error_users.append(User.get_full_name(user.id))
                    print("-- Alert Authority axis: ", e)
            error_text = '' if len(
                error_users) == 0 else '\nСообщения следующим пользователям не доставлены (см. логи): ' + ', '.join(
                error_users)
            bot.send_message(chat_id, 'Успешно' + error_text, reply_markup=getKeyboard(user_id))
            setState(user_id, 1)
    elif state == 101:
        if text == back_btn:
            bot.send_message(chat_id, 'Функции администратора', reply_markup=getAdminKeyboard())
            setState(user_id, 1)
        elif text == 'Да':
            voting_id, users_summary = getUsersSummaryFromVoting()
            if voting_id is None:
                bot.send_message(chat_id, 'В настоящее время нет активной оценки', reply_markup=getAdminKeyboard())
                setState(user_id, 1)
            for user in users_summary:
                try:
                    bot.send_message(user, 'Сегодня были сформированы предварительные результаты ежемесячной оценки')
                    keyboard = InlineKeyboardMarkup()
                    keyboard.add(InlineKeyboardButton('Детали', callback_data=f"votingdetails_{user}_{voting_id}_3"))
                    bot.send_message(user,
                                     f'По оси Власти вам выставили следующие оценки:\n\tУправляемость - {markFromUserSummary(users_summary[user], "7")}\n\tСамоуправление - {markFromUserSummary(users_summary[user], "8")}\n\tСтратегия - {markFromUserSummary(users_summary[user], "9")}',
                                     reply_markup=keyboard)
                    keyboard = InlineKeyboardMarkup()
                    keyboard.add(InlineKeyboardButton('Детали', callback_data=f"votingdetails_{user}_{voting_id}_1"))
                    bot.send_message(user,
                                     f'По оси Отношений вам выставили следующие оценки:\n\tЯсность позиции - {markFromUserSummary(users_summary[user], "2")}\n\tЭнергия - {markFromUserSummary(users_summary[user], "3")}\n\tЛичностный рост - {markFromUserSummary(users_summary[user], "1")}',
                                     reply_markup=keyboard)
                    keyboard = InlineKeyboardMarkup()
                    keyboard.add(InlineKeyboardButton('Детали', callback_data=f"votingdetails_{user}_{voting_id}_2"))
                    bot.send_message(user,
                                     f'По оси Дела вам выставили следующие оценки:\n\tДвижение - {markFromUserSummary(users_summary[user], "4")}\n\tЗавершенность - {markFromUserSummary(users_summary[user], "5")}\n\tПодтверждение средой - {markFromUserSummary(users_summary[user], "6")}',
                                     reply_markup=keyboard)
                except ApiException as e:
                    print(f"Exception for user with chat_id {user}: {str(e)}")
            bot.send_message(chat_id, 'Результаты разосланы', reply_markup=getAdminKeyboard())
            setState(user_id, 1)
        else:
            keyboard = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            keyboard.add('Да')
            keyboard.add(back_btn)
            bot.send_message(chat_id, 'Неизвестный ответ. Разослать всем участвующим в оценке предварительные результаты?',
                             reply_markup=keyboard)


def process_image(message):
    if getState(message['from']['id']) == 2:
        photo = message['photo'][len(message['photo']) - 1]['file_id']
        _id = message['from']['id']
        photo_url = 'https://api.telegram.org/file/bot' + bot_config.token + '/' + bot.get_file(photo).file_path
        f = open(r'/home/snapper/KorpusToken/app/static/user_photos/user' + str(get_id(message['from']['id'])) + '.jpg',
                 "wb")
        ufr = requests.get(photo_url)
        f.write(ufr.content)
        f.close()
        setPhoto(_id, photo_url)
        # bot.send_photo(message['chat']['id'], photo)
        markup = InlineKeyboardMarkup()
        fields = ActivityField.query.all()
        buttons = [InlineKeyboardButton(text=field.name, callback_data=f"set-field-{field.id}") for field in fields]
        button_chunks = [buttons[offs:offs+4] for offs in range(0, len(buttons), 4)]
        for chunk in button_chunks:
            markup.row(*chunk)
        markup.add(InlineKeyboardButton(text='Подтвердить выбор', callback_data='complete-setting-fields'))
        bot.send_message(message['chat']['id'], 'Выберите до 3 сфер, наиболее точно отражающих фокус вашей текущей деятельности и экспертизы.', reply_markup=markup)


def get_mark_message(user_id, team_id):
    today = datetime.date(datetime.datetime.now().year, datetime.datetime.now().month,
                          datetime.datetime.now().day)
    mark1 = WeeklyVoting.query.filter(WeeklyVoting.user_id == get_id(user_id), WeeklyVoting.team_id == team_id,
                                      WeeklyVoting.criterion_id == 4, WeeklyVoting.date == today).first()
    if mark1:
        mark1 = mark1.mark
    else:
        mark1 = 0
    mark2 = WeeklyVoting.query.filter(WeeklyVoting.user_id == get_id(user_id), WeeklyVoting.team_id == team_id,
                                      WeeklyVoting.criterion_id == 5, WeeklyVoting.date == today).first()
    if mark2:
        mark2 = mark2.mark
    else:
        mark2 = 0
    mark3 = WeeklyVoting.query.filter(WeeklyVoting.user_id == get_id(user_id), WeeklyVoting.team_id == team_id,
                                      WeeklyVoting.criterion_id == 6, WeeklyVoting.date == today).first()
    if mark3:
        mark3 = mark3.mark
    else:
        mark3 = 0
    team = Teams.query.filter_by(id=team_id).first().name
    message = '<b>Команда "{}" </b>\nДвижение: {}\nЗавершенность: {}\nПодтверждение средой: {}\n\n'.format(team, mark1,
                                                                                                           mark2, mark3)
    return message


def get_cadets_for_choosing(team_id, user_id):
    today = datetime.date(datetime.datetime.now().year, datetime.datetime.now().month,
                          datetime.datetime.now().day)
    team = Membership.get_crew_of_team(team_id)
    res = []
    for member in team:
        if WeeklyVotingMembers.query.filter(WeeklyVotingMembers.team_id == team_id,
                                            WeeklyVotingMembers.cadet_id == member[0],
                                            WeeklyVotingMembers.date == today,
                                            WeeklyVotingMembers.user_id == user_id).first() is None:
            res.append((member[0], member[1] + " " + member[2]))
    return res


def process_callback(callback):
    data = callback['data']
    user_id = callback['from']['id']
    user = User.query.filter_by(tg_id=user_id).first()
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
                                           func.month(Voting.date) == month,
                                           Voting.axis_id == 1).all()) < marked_teams_num:
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
            users = [user for user in User.query.all() if (User.check_expert(user.id) or User.check_tracker(user.id) or
                                                           User.check_teamlead(user.id))]
            user_names = list()
            month = datetime.datetime.now().month
            marked_teams_num = len(Teams.query.filter_by(type=1).all())
            for user in users:
                if len(Voting.query.filter(Voting.user_id == user.id,
                                           func.month(Voting.date) == month,
                                           Voting.axis_id == 2).all()) < marked_teams_num:
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
    elif data.startswith('choose_team_for_wv_'):
        tid = int(data.split('_')[-1])
        cadet_id = get_id(user_id)
        bot.delete_message(chat_id=chat_id, message_id=message_id)
        if tid == 0:
            bot.send_message(chat_id, 'Главное меню', reply_markup=getKeyboard(user_id))
        else:
            team = get_cadets_for_choosing(tid, user_id)
            markup = InlineKeyboardMarkup()
            for cadet in team:
                markup.add(InlineKeyboardButton(text=cadet[1],
                                                callback_data='choose_members_for_wv_{}_{}'.format(tid, cadet[0])))
            markup.add(InlineKeyboardButton(text='<Закончить выбор>',
                                            callback_data='choose_members_for_wv_0_0'))
            # markup.add(InlineKeyboardButton(text='<Назад>', callback_data='choose_members_for_wv_0_0'))
            bot.send_message(chat_id, 'Выберите участников команды, которые получат баллы за текущую оценку',
                             reply_markup=markup)
    elif data.startswith('choose_team_'):
        tid = int(data.split('_')[-1])
        bot.delete_message(chat_id=chat_id, message_id=message_id)
        if tid == 0:
            bot.send_message(chat_id, 'Главное меню', reply_markup=getKeyboard(user_id))
        else:
            # team = get_cadets_for_choosing(tid, user_id)
            # markup = InlineKeyboardMarkup()
            # for cadet in team:
            #     markup.add(InlineKeyboardButton(text=cadet[1],
            #                                     callback_data='choose_members_for_wv_{}_{}'.format(tid, cadet[0])))
            # markup.add(InlineKeyboardButton(text='<Закончить выбор и перейти к оценке>',
            #                                 callback_data='choose_members_for_wv_1_0'))
            # markup.add(InlineKeyboardButton(text='<Назад>', callback_data='choose_members_for_wv_0_0'))
            # bot.send_message(chat_id, 'Выберите участников команды, которые получат баллы за текущую оценку',
            #                  reply_markup=markup)
            message = get_mark_message(user_id, tid)
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(text='Движение', callback_data='weekly_vote_{}_{}'.format(tid, 4)))
            markup.add(InlineKeyboardButton(text='Завершенность', callback_data='weekly_vote_{}_{}'.format(tid, 5)))
            markup.add(
                InlineKeyboardButton(text='Подтверждение средой', callback_data='weekly_vote_{}_{}'.format(tid, 6)))
            markup.add(InlineKeyboardButton(text='Зафиксировать результаты оценки',
                                            callback_data='weekly_vote_{}_{}'.format(tid, 0)))
            markup.add(InlineKeyboardButton(text='<Назад>', callback_data='weekly_vote_{}_{}'.format(0, 0)))
            bot.send_message(chat_id, message + 'Выберите критерий для оценки', reply_markup=markup, parse_mode='HTML')
    elif data.startswith('choose_members_for_wv_'):
        tid = int(data.split('_')[-2])
        cadet_id = int(data.split('_')[-1])
        bot.delete_message(chat_id=chat_id, message_id=message_id)
        if tid == 0:
            cadet_id = get_id(user_id)
            teams = Membership.query.filter_by(user_id=cadet_id).all()
            my_teams = []
            for t in teams:
                if TeamRoles.query.filter(TeamRoles.team_id == t.team_id, TeamRoles.user_id == cadet_id,
                                          TeamRoles.role_id == 1).first():
                    my_teams.append(t)
            my_teams_ids = [t.team_id for t in my_teams if Teams.query.filter_by(id=t.team_id).first().type in [1, 4]]
            if len(my_teams_ids) == 1:
                bot.send_message(chat_id, 'Главное меню', reply_markup=getKeyboard(user_id))
            else:
                markup = InlineKeyboardMarkup()
                for t_id in my_teams_ids:
                    team = Teams.query.get(t_id)
                    markup.add(InlineKeyboardButton(text=team.name, callback_data=f'choose_team_for_wv_{t_id}'))
                markup.add(InlineKeyboardButton(text='<Назад>', callback_data=f'choose_team_for_wv_0'))
                bot.send_message(chat_id,
                                 'Выберите команду для указания участников, которые получат баллы за текущую оценку',
                                 reply_markup=markup)
        elif cadet_id == 0:
            message = get_mark_message(user_id, tid)
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(text='Движение', callback_data='weekly_vote_{}_{}'.format(tid, 4)))
            markup.add(InlineKeyboardButton(text='Завершенность', callback_data='weekly_vote_{}_{}'.format(tid, 5)))
            markup.add(
                InlineKeyboardButton(text='Подтверждение средой', callback_data='weekly_vote_{}_{}'.format(tid, 6)))
            markup.add(InlineKeyboardButton(text='Зафиксировать результаты оценки',
                                            callback_data='weekly_vote_{}_{}'.format(tid, 0)))
            markup.add(InlineKeyboardButton(text='<Назад>', callback_data='weekly_vote_{}_{}'.format(0, 0)))
            bot.send_message(chat_id, message + 'Выберите критерий для оценки', reply_markup=markup, parse_mode='HTML')
        else:
            today = datetime.date(datetime.datetime.now().year, datetime.datetime.now().month,
                                  datetime.datetime.now().day)
            memeber = WeeklyVotingMembers(cadet_id=cadet_id, user_id=user_id, date=today, team_id=tid)
            db.session.add(memeber)
            db.session.commit()
            team = get_cadets_for_choosing(tid, user_id)
            markup = InlineKeyboardMarkup()
            for cadet in team:
                markup.add(InlineKeyboardButton(text=cadet[1],
                                                callback_data='choose_members_for_wv_{}_{}'.format(tid, cadet[0])))
            markup.add(InlineKeyboardButton(text='<Закончить выбор>',
                                            callback_data='choose_members_for_wv_0_0'))
            #markup.add(InlineKeyboardButton(text='<Назад>', callback_data='choose_members_for_wv_0_0'))
            bot.send_message(chat_id, 'Выберите участников команды, которые получат баллы за текущую оценку',
                             reply_markup=markup)
    elif data.startswith('weekly_vote_'):
        today = datetime.date(datetime.datetime.now().year, datetime.datetime.now().month,
                              datetime.datetime.now().day)
        tid = int(data.split('_')[-2])
        cid = int(data.split('_')[-1])
        if cid == 0:
            if tid == 0:
                teams = Teams.query.filter_by(type=1).all() + Teams.query.filter_by(type=4).all()
                markup = InlineKeyboardMarkup()
                for t in teams:
                    wm = WeeklyVoting.query.filter(WeeklyVoting.user_id == get_id(user_id),
                                                   WeeklyVoting.team_id == t.id,
                                                   WeeklyVoting.finished == 1,
                                                   WeeklyVoting.date == today).first()
                    if not wm:
                        markup.add(InlineKeyboardButton(text=t.name, callback_data='choose_team_{}'.format(t.id)))
                markup.add(InlineKeyboardButton(text='<Назад>', callback_data='choose_team_0'))
                bot.delete_message(chat_id=chat_id, message_id=message_id)
                bot.send_message(chat_id, 'Выберите команду для оценки', reply_markup=markup)
            else:
                mark1 = WeeklyVoting.query.filter(WeeklyVoting.user_id == get_id(user_id),
                                                  WeeklyVoting.team_id == tid,
                                                  WeeklyVoting.criterion_id == 4,
                                                  WeeklyVoting.finished == 0, WeeklyVoting.date == today).first()
                if mark1:
                    mark1.finished = 1
                else:
                    wm = WeeklyVoting(user_id=get_id(user_id), team_id=tid, criterion_id=4, mark=0,
                                      date=datetime.date(datetime.datetime.now().year, datetime.datetime.now().month,
                                                         datetime.datetime.now().day), finished=1)
                    db.session.add(wm)
                mark2 = WeeklyVoting.query.filter(WeeklyVoting.user_id == get_id(user_id),
                                                  WeeklyVoting.team_id == tid,
                                                  WeeklyVoting.criterion_id == 5, WeeklyVoting.finished == 0).first()
                if mark2:
                    mark2.finished = 1
                else:
                    wm = WeeklyVoting(user_id=get_id(user_id), team_id=tid, criterion_id=5, mark=0,
                                      date=datetime.date(datetime.datetime.now().year, datetime.datetime.now().month,
                                                         datetime.datetime.now().day), finished=1)
                    db.session.add(wm)
                mark3 = WeeklyVoting.query.filter(WeeklyVoting.user_id == get_id(user_id),
                                                  WeeklyVoting.team_id == tid,
                                                  WeeklyVoting.criterion_id == 6, WeeklyVoting.finished == 0,
                                                  WeeklyVoting.date == today).first()
                if mark3:
                    mark3.finished = 1
                else:
                    wm = WeeklyVoting(user_id=get_id(user_id), team_id=tid, criterion_id=6, mark=0,
                                      date=datetime.date(datetime.datetime.now().year, datetime.datetime.now().month,
                                                         datetime.datetime.now().day), finished=1)
                    db.session.add(wm)
                db.session.commit()
                teams = Teams.query.filter_by(type=1).all() + Teams.query.filter_by(type=4).all()
                markup = InlineKeyboardMarkup()
                for t in teams:
                    wm = WeeklyVoting.query.filter(WeeklyVoting.user_id == get_id(user_id),
                                                   WeeklyVoting.team_id == t.id,
                                                   WeeklyVoting.finished == 1,
                                                   WeeklyVoting.date == today).first()
                    if not wm:
                        markup.add(InlineKeyboardButton(text=t.name, callback_data='choose_team_{}'.format(t.id)))
                markup.add(InlineKeyboardButton(text='<Назад>', callback_data='choose_team_0'))
                bot.delete_message(chat_id=chat_id, message_id=message_id)
                bot.send_message(chat_id, 'Выберите команду для оценки', reply_markup=markup)
        else:
            wm = WeeklyVoting.query.filter(WeeklyVoting.user_id == get_id(user_id), WeeklyVoting.team_id == tid,
                                           WeeklyVoting.criterion_id == cid, WeeklyVoting.date == today).first()
            if wm:
                wm.mark = abs(wm.mark - 1)
                db.session.commit()
            else:
                wm = WeeklyVoting(user_id=get_id(user_id), team_id=tid, criterion_id=cid, mark=1,
                                  date=datetime.date(datetime.datetime.now().year, datetime.datetime.now().month,
                                                     datetime.datetime.now().day), finished=0)
                db.session.add(wm)
                db.session.commit()
            message = get_mark_message(user_id, tid)
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(text='Движение', callback_data='weekly_vote_{}_{}'.format(tid, 4)))
            markup.add(InlineKeyboardButton(text='Завершенность', callback_data='weekly_vote_{}_{}'.format(tid, 5)))
            markup.add(
                InlineKeyboardButton(text='Подтверждение средой', callback_data='weekly_vote_{}_{}'.format(tid, 6)))
            markup.add(InlineKeyboardButton(text='Зафиксировать результаты оценки',
                                            callback_data='weekly_vote_{}_{}'.format(tid, 0)))
            markup.add(InlineKeyboardButton(text='<Назад>', callback_data='weekly_vote_{}_{}'.format(0, 0)))
            bot.edit_message_text(message + 'Выберите критерий для оценки', chat_id, message_id, parse_mode='HTML',
                                  reply_markup=markup)
            # bot.send_message(chat_id, message + 'Выберите критерий для оценки', reply_markup=markup, parse_mode='HTML')
    elif data.startswith('details_'):
        items = data.split('_')
        team_id = int(items[1])
        date = datetime.datetime.strptime(items[2], '%d.%m.%Y')
        user_id = int(items[3])
        text = 'Вот как вас оценили:\n<b>Движение</b>\n'
        marks = WeeklyVoting.query.filter(WeeklyVoting.date == date, WeeklyVoting.team_id == team_id,
                                          WeeklyVoting.criterion_id == 4, WeeklyVoting.finished == 1).all()
        for mark in marks:
            user = User.query.get(mark.user_id)
            text += f'<i>{User.get_full_name(user.id)}</i> (@{user.tg_nickname}): {mark.mark}\n'
        text += '\n<b>Завершённость</b>\n'
        marks = WeeklyVoting.query.filter(WeeklyVoting.date == date, WeeklyVoting.team_id == team_id,
                                          WeeklyVoting.criterion_id == 5, WeeklyVoting.finished == 1).all()
        for mark in marks:
            user = User.query.get(mark.user_id)
            text += f'<i>{User.get_full_name(user.id)}</i> (@{user.tg_nickname}): {mark.mark}\n'
        text += '\n<b>Подтверждение средой</b>\n'
        marks = WeeklyVoting.query.filter(WeeklyVoting.date == date, WeeklyVoting.team_id == team_id,
                                          WeeklyVoting.criterion_id == 6, WeeklyVoting.finished == 1).all()
        for mark in marks:
            user = User.query.get(mark.user_id)
            text += f'<i>{User.get_full_name(user.id)}</i> (@{user.tg_nickname}): {mark.mark}\n'
        text += '\nВы можете запросить комментарий у любого из оценивающих. Если, на ваш взгляд, результаты искажены из-за технической ошибки, обратитесь к @robertlengdon'
        bot.send_message(chat_id, text, parse_mode='HTML')
    elif data.startswith('votingdetails_'):
        items = data.split('_')
        user_chat_id = int(items[1])
        voting_id = int(items[2])
        axis_id = int(items[3])
        user_id = User.query.filter_by(chat_id=user_chat_id).first().id

        criterion_dict = {1: {1: 'Личностный рост', 2: 'Ясность позиции', 3: 'Энергия'},
                          2: {4: 'Движение', 5: 'Завершенность', 6: 'Подтверждение средой'},
                          3: {7: 'Управляемость', 8: 'Самоуправление', 9: 'Стратегия'}}
        criterions = criterion_dict[axis_id]
        text = 'Вот как вас оценили:\n'
        for c_id in criterions:
            text += f"<b>{criterions[c_id]}</b>\n"
            teams = Membership.query.filter_by(user_id=user_id).all()
            teams = [team.team_id for team in teams] + [0]
            votings = []
            for t in teams:
                votings += Voting.query.filter(Voting.voting_id == voting_id, Voting.axis_id == axis_id,
                                               Voting.team_id == t).all()
            for v in votings:
                cur_user = User.query.get(v.user_id)
                mark = VotingInfo.query.filter(VotingInfo.criterion_id == c_id, VotingInfo.cadet_id == user_id, VotingInfo.voting_id == v.id).first()
                text += f'<i>{User.get_full_name(cur_user.id)}</i> (@{cur_user.tg_nickname}): {mark.mark}\n'
        text += '\nВы можете запросить комментарий у любого из оценивающих. Если, на ваш взгляд, результаты искажены из-за технической ошибки, обратитесь к @robertlengdon'
        bot.send_message(user_chat_id, text, parse_mode='HTML')
    elif data.startswith('set-field'):
        user_fields_count = UserActivityField.query.filter_by(user_id=user.id).count()
        if user_fields_count == 3:
            return bot.send_message(chat_id, 'Нельзя выбрать больше трёх сфер деятельности.')
        field_id = data[len('set-field-'):]
        field = ActivityField.query.filter_by(id=field_id).first()
        user_field = UserActivityField.query.filter_by(field_id=field_id, user_id=user.id).first()
        if field:
            if user_field:
                db.session.delete(user_field)
            else:
                db.session.add(UserActivityField(user_id=user.id, field_id=field.id))
            db.session.commit()
        markup = InlineKeyboardMarkup()
        fields = ActivityField.query.all()
        user_fields = UserActivityField.query.filter_by(user_id=user.id).all()
        buttons = [InlineKeyboardButton(text=f"{field.name}{'🌟' if any(element.field_id == field.id for element in user_fields) else ''}", callback_data=f"set-field-{field.id}") for field in fields]
        button_chunks = [buttons[offs:offs+4] for offs in range(0, len(buttons), 4)]
        for chunk in button_chunks:
            markup.row(*chunk)
        markup.add(InlineKeyboardButton(text='Подтвердить выбор', callback_data='complete-setting-fields'))
        bot.send_message(chat_id, 'Выберите до 3 сфер, наиболее точно отражающих фокус вашей текущей деятельности и экспертизы.', reply_markup=markup)
    elif data == 'complete-setting-fields':
        user_fields_count = UserActivityField.query.filter_by(user_id=user.id).count()
        if user_fields_count == 0:
            return bot.send_message(chat_id, 'Пожалуйста, выберите сферы вашей деятельности.')
        bot.send_message(chat_id, 'Добро пожаловать!', reply_markup=getKeyboard(user_id))
        setState(user_id, 1)
    elif data == 'register_via_bot':
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text='Отмена', callback_data='cancel_registration'))
        in_memory_storage.hset(f"tg_user:{user_id}", mapping={
            'bot_registration_state': 'firstname_requested',
            'firstname': '',
            'lastname': '',
            'login': ''})
        bot.send_message(chat_id, 'Добро пожаловать в сообщество Korpus. Пожалуйста, введите ваше Имя', reply_markup=markup)
    elif data == 'cancel_registration':
        in_memory_storage.delete(f"tg_user:{user_id}")
        start(callback['message'])


def start(message):
    tg_user_info = in_memory_storage.hgetall(f"tg_user:{message['from']['id']}")
    if isUserInDb(message['from']['username']):
        if not (checkBotRegistration(message['from']['username'], message['from']['id'], message['chat']['id'])):
            bot.send_message(message['chat']['id'],
                             "Для упрощения нашего взаимодействия через систему загрузите, пожалуйста, свою фотографию. Обратите внимание, что фотографию надо присылать в сжатом виде и не в качестве прикрепляемого документа")
            setState(message['from']['id'], 2)
        else:
            setState(message['from']['id'], 1)
            bot.send_message(message['chat']['id'],
                             "С возвращением!", reply_markup=getKeyboard(message['from']['id']))
    elif tg_user_info.get(b'bot_registration_state') == b'firstname_requested':
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text='Отмена', callback_data='cancel_registration'))
        tg_user_info[b'bot_registration_state'] = 'lastname_requested'
        tg_user_info[b'firstname'] = message['text']
        in_memory_storage.hset(f"tg_user:{message['from']['id']}", mapping=tg_user_info)
        bot.send_message(message['chat']['id'], 'Введите вашу Фамилию', reply_markup=markup)
    elif tg_user_info.get(b'bot_registration_state') == b'lastname_requested':
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text='Отмена', callback_data='cancel_registration'))
        tg_user_info[b'bot_registration_state'] = 'login_requested'
        tg_user_info[b'lastname'] = message['text']
        in_memory_storage.hset(f"tg_user:{message['from']['id']}", mapping=tg_user_info)
        bot.send_message(message['chat']['id'], 'Для доступа к личному кабинету вам необходимо придумать Логин. Пожалуйста, введите логин', reply_markup=markup)
    elif tg_user_info.get(b'bot_registration_state') == b'login_requested':
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text='Отмена', callback_data='cancel_registration'))
        tg_user_info[b'bot_registration_state'] = 'password_requested'
        tg_user_info[b'login'] = message['text']
        in_memory_storage.hset(f"tg_user:{message['from']['id']}", mapping=tg_user_info)
        bot.send_message(message['chat']['id'], 'Придумайте пароль для доступа к личному кабинету', reply_markup=markup)
    elif tg_user_info.get(b'bot_registration_state') == b'password_requested':
        eth_account = Account.create()
        user = User(
            email='',
            login=tg_user_info[b'login'],
            tg_nickname=message['from']['username'],
            courses='',
            birthday='',
            education='Unknown',
            work_exp='',
            sex='',
            name=tg_user_info[b'firstname'],
            surname=tg_user_info[b'lastname'],
            private_key=eth_account.key.hex())
        user.set_password(message['text'])
        db.session.add(user)
        db.session.commit()
        setStatusByID(user.id, 3)
        in_memory_storage.delete(f"tg_user:{message['from']['id']}")
        start(message)
    else:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text='Регистрация через сайт', url='http://lk.korpus.io/'))
        markup.add(InlineKeyboardButton(text='Регистрация через бота', callback_data='register_via_bot'))
        bot.send_message(message['chat']['id'],
                         """Кажется, ты еще не зарегистрирован в системе. Выбери удобный вариант регистрации""",
                         reply_markup=markup)
