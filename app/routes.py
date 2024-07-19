from app import bot, in_memory_storage, jira_webhook_url, jira_api_url
import bot_config
from db_commands import *
from sqlalchemy import func
from flask import request, blueprints
#from eth_account import Account
import jira_fields
import traceback
import requests
from requests.auth import HTTPBasicAuth
from telebot.apihelper import ApiException
from datetime import datetime

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
        print(traceback.format_exc())
    finally:
        return "Message Processed"


def process_text(message):
    text = message['text']
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    tg_user_info = in_memory_storage.hgetall(f"tg_user:{user_id}")
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
        elif text == bug_report_btn:
            in_memory_storage.hset(f"tg_user:{user_id}", mapping={'dialog_state': 'bug_report'})
            bot.send_message(chat_id, 'Пожалуйста опишите с какой проблемой вы столкнулись и отправьте сообщение')
        elif tg_user_info.get(b'dialog_state') == b'bug_report':
            in_memory_storage.delete(f"tg_user:{message['from']['id']}")
            requests.post(jira_webhook_url, json={'data': {'username': message['from']['first_name'], 'description': message['text'], 'chat_id': chat_id}})
            bot.send_message(chat_id, 'На основе вашего сообщения была создана задача, она будет решена в ближайшее время. Благодарим за обратную связь!')
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
                return
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
    elif state == 200:
        extra = getExtra(user_id)
        items = extra.split('_')
        voting_id = int(items[1])
        criterion_id = int(items[0])
        axis_id = int(items[2])
        cadet_id = int(items[3])
        mark = int(items[4])
        setState(user_id, 1)
        bot.send_message(chat_id, 'Комментарий отправлен', reply_markup=getKeyboard(user_id))
        admins = getAdmins()
        axises = {1: 'Отношений', 2: 'Дела', 3: 'Власти'}
        criterions = {1: 'Личностный рост', 2: 'Ясность позиции', 3: 'Энергия', 4: 'Движение', 5: 'Завершенность',
                      6: 'Подтверждение средой', 7: 'Управляемость', 8: 'Самоуправление', 9: 'Стратегия'}
        for admin in admins:
            bot.send_message(admin.chat_id,
                             f'Ранее <b>{User.get_full_name(cadet_id)}</b> запросил комментарий у <b>{User.get_full_name(get_id(user_id))}</b> по оси <b>{axises[axis_id]}</b>, критерий <b>{criterions[criterion_id]}</b>, оценка <b>{mark}</b>\n{User.get_full_name(get_id(user_id))} отправил комментарий',
                             parse_mode='HTML')
        user_chat_id = User.query.get(cadet_id).chat_id
        user_markup = InlineKeyboardMarkup()
        user_markup.add(InlineKeyboardButton(text='Принято',
                                             callback_data=f'acceptcomment_{criterion_id}_{voting_id}_{axis_id}_{user_id}_{mark}'))
        user_markup.add(InlineKeyboardButton(text='Не принято',
                                             callback_data=f'denycomment_{criterion_id}_{voting_id}_{axis_id}_{user_id}_{mark}'))
        bot.send_message(user_chat_id,
                         f'Вы запрашивали комментарий у  <b>{User.get_full_name(get_id(user_id))}</b> по поводу оценки по критерию “<b>{criterions[criterion_id]}</b>“ оси <b>{axises[axis_id]}</b>\nКомментарий: <i>{text}</i>',
                         reply_markup=user_markup, parse_mode='HTML')


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
    tg_user_info = in_memory_storage.hgetall(f"tg_user:{user_id}")
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
        users1, users2, users3 = [], [], []
        for mark in marks:
            user = User.query.get(mark.user_id)
            if user.id not in users1 and user.id != user_id:
                users1.append(user.id)
                text += f'<i>{User.get_full_name(user.id)}</i> (@{user.tg_nickname}): {mark.mark}\n'
        text += '\n<b>Завершённость</b>\n'
        marks = WeeklyVoting.query.filter(WeeklyVoting.date == date, WeeklyVoting.team_id == team_id,
                                          WeeklyVoting.criterion_id == 5, WeeklyVoting.finished == 1).all()
        for mark in marks:
            user = User.query.get(mark.user_id)
            if user.id not in users2:
                users2.append(user.id)
                text += f'<i>{User.get_full_name(user.id)}</i> (@{user.tg_nickname}): {mark.mark}\n'
        text += '\n<b>Подтверждение средой</b>\n'
        marks = WeeklyVoting.query.filter(WeeklyVoting.date == date, WeeklyVoting.team_id == team_id,
                                          WeeklyVoting.criterion_id == 6, WeeklyVoting.finished == 1).all()
        for mark in marks:
            user = User.query.get(mark.user_id)
            if user.id not in users3:
                users3.append(user.id)
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
            users = []
            for v in votings:
                cur_user = User.query.get(v.user_id)
                mark = VotingInfo.query.filter(VotingInfo.criterion_id == c_id, VotingInfo.cadet_id == user_id, VotingInfo.voting_id == v.id).first()
                mark = mark.mark if mark else 0
                username = User.get_full_name(cur_user.id)
                if username not in users and cur_user.id != user_id:
                    users.append(username)
                    text += f'<i>{username}</i> (@{cur_user.tg_nickname}): {mark}\n'
        text += '\nНажмите <b>Обратная связь</b>, если хотите получить комментарий по выставленным оценкам.\nЕсли, на ваш взгляд, результаты искажены из-за технической ошибки, обратитесь к @robertlengdon.\nЕсли у вас нет вопросов по выставленным оценкам, просто проигнорируйте это сообщение.'
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text='Обратная связь', callback_data=f'feedback1_{axis_id}_{voting_id}'))
        bot.send_message(user_chat_id, text, parse_mode='HTML', reply_markup=markup)
    elif data.startswith('feedback1'):
        items = data.split('_')
        voting_id = int(items[2])
        axis_id = int(items[1])
        criterion_dict = {1: {1: 'Личностный рост', 2: 'Ясность позиции', 3: 'Энергия'},
                          2: {4: 'Движение', 5: 'Завершенность', 6: 'Подтверждение средой'},
                          3: {7: 'Управляемость', 8: 'Самоуправление', 9: 'Стратегия'}}
        criterions = criterion_dict[axis_id]
        markup = InlineKeyboardMarkup()
        for c_id in criterions:
            markup.add(InlineKeyboardButton(text=criterions[c_id],
                                            callback_data=f'feedback2_{c_id}_{voting_id}_{axis_id}'))
        bot.send_message(chat_id, 'Выберите критерий, по которому хотите получить комментарий', parse_mode='HTML', reply_markup=markup)
    elif data.startswith('feedback2'):
        items = data.split('_')
        voting_id = int(items[2])
        criterion_id = int(items[1])
        axis_id = int(items[3])
        markup = InlineKeyboardMarkup()
        teams = Membership.query.filter_by(user_id=get_id(user_id)).all()
        teams = [team.team_id for team in teams] + [0]
        votings = []
        for t in teams:
            votings += Voting.query.filter(Voting.voting_id == voting_id, Voting.axis_id == axis_id,
                                           Voting.team_id == t).all()
        for v in votings:
            cur_user = User.query.get(v.user_id)
            mark = VotingInfo.query.filter(VotingInfo.criterion_id == criterion_id, VotingInfo.cadet_id == user_id,
                                           VotingInfo.voting_id == v.id).first()
            mark = mark.mark if mark else 0
            markup.add(InlineKeyboardButton(text=User.get_full_name(cur_user.id),
                                            callback_data=f'feedback3_{criterion_id}_{voting_id}_{axis_id}_{cur_user.id}_{mark}'))
        markup.add(InlineKeyboardButton(text='Завершить', callback_data=f'feedback3_0_0_0_0_0'))
        bot.send_message(chat_id, 'Выберите члена коллегии, чей комментарий вы хотите получить', parse_mode='HTML',
                         reply_markup=markup)
    elif data.startswith('feedback3'):
        items = data.split('_')
        voting_id = int(items[2])
        criterion_id = int(items[1])
        axis_id = int(items[3])
        cur_user_id = int(items[4])
        try:
            mark = int(items[5])
        except:
            mark = 0
        if cur_user_id > 0:
            admins = getAdmins()
            axises = {1: 'Отношений', 2:'Дела', 3: 'Власти'}
            criterions = {1: 'Личностный рост', 2: 'Ясность позиции', 3: 'Энергия', 4: 'Движение', 5: 'Завершенность',
                          6: 'Подтверждение средой',7: 'Управляемость', 8: 'Самоуправление', 9: 'Стратегия'}
            for admin in admins:
                print(admin.chat_id)
                bot.send_message(admin.chat_id, f'<b>{User.get_full_name(get_id(user_id))}</b> запросил комментарий у <b>{User.get_full_name(cur_user_id)}</b> по оси <b>{axises[axis_id]}</b>, критерий <b>{criterions[criterion_id]}</b>, оценка <b>{mark}</b>', parse_mode='HTML')
            user_chat_id = User.query.get(cur_user_id).chat_id
            user_markup = InlineKeyboardMarkup()
            user_markup.add(InlineKeyboardButton(text='Дать комментарий',
                                                callback_data=f'comment_{criterion_id}_{voting_id}_{axis_id}_{get_id(user_id)}_{mark}'))
            bot.send_message(user_chat_id, f'Пользователь <b>{User.get_full_name(get_id(user_id))}</b> запросил комментарий по выставленной вами оценке <b>{mark}</b> по критерию “<b>{criterions[criterion_id]}</b>“ оси <b>{axises[axis_id]}</b>\nПожалуйста, дайте максимально развернутый комментарий, нажав кнопку “Дать комментарий“.\nОзнакомиться с данными, на основании которых вы выставляли оценку, можно тут - http://lk.korpus.io/voting_summary?axis_id={axis_id}', reply_markup=user_markup, parse_mode='HTML')

            markup = InlineKeyboardMarkup()
            teams = Membership.query.filter_by(user_id=user_id).all()
            teams = [team.team_id for team in teams] + [0]
            votings = []
            for t in teams:
                votings += Voting.query.filter(Voting.voting_id == voting_id, Voting.axis_id == axis_id,
                                               Voting.team_id == t).all()
            for v in votings:
                cur_user = User.query.get(v.user_id)
                mark = VotingInfo.query.filter(VotingInfo.criterion_id == criterion_id, VotingInfo.cadet_id == user_id,
                                               VotingInfo.voting_id == v.id).first()
                mark = mark.mark if mark else 0
                markup.add(InlineKeyboardButton(text=User.get_full_name(cur_user.id),
                                                callback_data=f'feedback3_{criterion_id}_{voting_id}_{axis_id}_{cur_user.id}_{mark}'))
            markup.add(InlineKeyboardButton(text='Завершить', callback_data=f'feedback3_0_0_0_0_0'))
            bot.send_message(chat_id, f'<b>{User.get_full_name(cur_user_id)}</b> получил ваш запрос на комментарий к оценке. Выберите члена коллегии, чей ещё комментарий вы хотели бы получить, или нажмите “Завершить“', parse_mode='HTML',
                             reply_markup=markup)
        else:
            bot.send_message(chat_id, 'Главное меню', reply_markup=getKeyboard(user_id))

    elif data.startswith('comment'):
        items = data.split('_')
        voting_id = int(items[2])
        criterion_id = int(items[1])
        axis_id = int(items[3])
        cadet_id = int(items[4])
        mark = int(items[5])
        setState(user_id, 200)
        setExtra(user_id, f'{criterion_id}_{voting_id}_{axis_id}_{cadet_id}_{mark}')
        bot.send_message(chat_id, 'Введите и отправьте сообщение с текстом комментария')

    elif data.startswith('acceptcomment'):
        items = data.split('_')
        voting_id = int(items[2])
        criterion_id = int(items[1])
        axis_id = int(items[3])
        voter_id = int(items[4])
        mark = int(items[5])
        bot.send_message(chat_id, 'Отлично. Вопрос закрыт')
        admins = getAdmins()
        axises = {1: 'Отношений', 2: 'Дела', 3: 'Власти'}
        criterions = {1: 'Личностный рост', 2: 'Ясность позиции', 3: 'Энергия', 4: 'Движение', 5: 'Завершенность',
                      6: 'Подтверждение средой', 7: 'Управляемость', 8: 'Самоуправление', 9: 'Стратегия'}
        for admin in admins:
            bot.send_message(admin.chat_id,
                             f'Ранее <b>{User.get_full_name(get_id(user_id))}</b> запросил комментарий у <b>{User.get_full_name(get_id(voter_id))}</b> по оси <b>{axises[axis_id]}</b>, критерий <b>{criterions[criterion_id]}</b>, оценка <b>{mark}</b>\n{User.get_full_name(get_id(voter_id))} отправил комментарий\n{User.get_full_name(get_id(user_id))} принял комментарий',
                             parse_mode='HTML')

    elif data.startswith('denycomment'):
        items = data.split('_')
        voting_id = int(items[2])
        criterion_id = int(items[1])
        axis_id = int(items[3])
        voter_id = int(items[4])
        mark = int(items[5])
        voter = User.query.filter_by(tg_id=voter_id).first()
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text='Разобрались', callback_data=f'razobr_{criterion_id}_{voting_id}_{axis_id}_{voter_id}_{mark}'))
        bot.send_message(chat_id, f'Для более детального разбора вашего случая, пожалуйста, свяжитесь с @{voter.tg_nickname}. После решения вашего вопроса, вернитесь к этому сообщению и нажмите кнопку “Разобрались“', reply_markup=markup)
        admins = getAdmins()
        axises = {1: 'Отношений', 2: 'Дела', 3: 'Власти'}
        criterions = {1: 'Личностный рост', 2: 'Ясность позиции', 3: 'Энергия', 4: 'Движение', 5: 'Завершенность',
                      6: 'Подтверждение средой', 7: 'Управляемость', 8: 'Самоуправление', 9: 'Стратегия'}
        for admin in admins:
            bot.send_message(admin.chat_id,
                             f'Ранее <b>{User.get_full_name(get_id(user_id))}</b> запросил комментарий у <b>{User.get_full_name(get_id(voter_id))}</b> по оси <b>{axises[axis_id]}</b>, критерий <b>{criterions[criterion_id]}</b>, оценка <b>{mark}</b>\n{User.get_full_name(get_id(voter_id))} отправил комментарий\n{User.get_full_name(get_id(user_id))} не принял комментарий',
                             parse_mode='HTML')
        cur_user = User.query.filter_by(tg_id=user_id).first()
        bot.send_message(voter.chat_id,f'Ранее <b>{User.get_full_name(get_id(user_id))}</b> запросил у вас комментарий по оси <b>{axises[axis_id]}</b>, критерий <b>{criterions[criterion_id]}</b>, оценка <b>{mark}</b>\nВы отправили комментарий.\n{User.get_full_name(get_id(user_id))} не принял комментарий, для решения этого вопроса, пожалуйста свяжитесь с @{cur_user.tg_nickname}',
                             parse_mode='HTML')

    elif data.startswith('razobr'):
        items = data.split('_')
        voting_id = int(items[2])
        criterion_id = int(items[1])
        axis_id = int(items[3])
        voter_id = int(items[4])
        mark = int(items[5])
        bot.send_message(chat_id, 'Отлично! Вопрос закрыт.')
        admins = getAdmins()
        axises = {1: 'Отношений', 2: 'Дела', 3: 'Власти'}
        criterions = {1: 'Личностный рост', 2: 'Ясность позиции', 3: 'Энергия', 4: 'Движение', 5: 'Завершенность',
                      6: 'Подтверждение средой', 7: 'Управляемость', 8: 'Самоуправление', 9: 'Стратегия'}
        for admin in admins:
            bot.send_message(admin.chat_id,
                             f'Ранее <b>{User.get_full_name(get_id(user_id))}</b> запросил комментарий у <b>{User.get_full_name(get_id(voter_id))}</b> по оси <b>{axises[axis_id]}</b>, критерий <b>{criterions[criterion_id]}</b>, оценка <b>{mark}</b>\n{User.get_full_name(get_id(voter_id))} отправил комментарий\n{User.get_full_name(get_id(user_id))} не принял комментарий\n{User.get_full_name(get_id(user_id))} отметил вопрос как решёный',
                             parse_mode='HTML')

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
        waiting_users = User.query.filter_by(registration_state=1).count()
        if waiting_users == 0:
            send_next_registration_request(user_id)
        setRegistrationState(user_id, 1)
        bot.send_message(chat_id, 'Спасибо за регистрацию! Вы в очереди на рассмотрение. Сообщим, как только обработаем вашу заявку.')
        setState(user_id, 1)
    elif data.startswith("accept-registration_"):
        if not user.is_community_manager:
            return
        accepted_user_id = data.split("_")[1]
        if not accepted_user_id:
            return None
        accepted_user = User.query.filter_by(tg_id=accepted_user_id).first()
        if accepted_user is None:
            return
        if accepted_user.is_full_registered:
            return bot.send_message(user_id, "Пользователь уже одобрен")
        setRegistrationState(accepted_user_id, 2)
        remove_registration_keyboards(accepted_user.id)
        managers = User.query.filter(User.statuses.any(UserStatuses.status_id == 11)).all()
        for manager in managers:
            bot.send_message(manager.chat_id, "Пользователь одобрен")
        send_next_registration_request(None)
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(text='В личный кабинет', url="https://lk.korpus.io"))
        bot.send_message(accepted_user.chat_id, "Ваша регистрация была одобрена.", reply_markup=keyboard)
        bot.send_message(accepted_user.chat_id, "Добро пожаловать!", reply_markup=getKeyboard(user_id))
    elif data.startswith("reject-registration_"):
        if not user.is_community_manager:
            return
        rejected_user_id = data.split("_")[1]
        if not rejected_user_id:
            return None
        rejected_user = User.query.filter_by(tg_id=rejected_user_id).first()
        if rejected_user is None:
            return
        if rejected_user.is_registration_rejected:
            return bot.send_message(user_id, "Пользователь уже отклонен")
        setRegistrationState(rejected_user_id, 3)
        rejected_user.registration_rejected_at = datetime.now()
        db.session.commit()
        remove_registration_keyboards(rejected_user.id)
        managers = User.query.filter(User.statuses.any(UserStatuses.status_id == 11)).all()
        for manager in managers:
            bot.send_message(manager.chat_id, "Пользователь отклонен")
        send_next_registration_request(None)
        bot.send_message(
            rejected_user.chat_id,
            "К сожалению, ваша регистрация была отклонена. Для получения дополнительной информации, пожалуйста, свяжитесь с нашим коммьюнити менеджером."
        )
    elif data == 'cancel_registration':
        in_memory_storage.delete(f"tg_user:{user_id}")
        start(callback['message'])


def send_next_registration_request(user_id):
    user = User.query.filter_by(tg_id=user_id).first() if user_id is not None else \
        User.query.filter_by(registration_state=1).order_by(User.registration_rejected_at.desc()).first()
    managers = User.query.filter(User.statuses.any(UserStatuses.status_id == 11)).all()
    keyboard = getRegistrationControlKeyboard(user.tg_id)
    for manager in managers:
        with open(r'/home/snapper/KorpusToken/app/static/user_photos/user' + str(user.id) + '.jpg', 'rb') as photo:
            res = bot.send_photo(
                manager.chat_id,
                photo,
                caption=f"{user.name} {user.surname} оставил заявку на регистрацию.",
                reply_markup=keyboard,
            )
            message_record = UserRegistrationMessage(
                chat_id=manager.chat_id,
                message_id=res.message_id,
                user_id=user.id
            )
            db.session.add(message_record)
        db.session.commit()


def remove_registration_keyboards(user_id):
    registration_messages = UserRegistrationMessage.query.filter_by(user_id=user_id).all()
    for message in registration_messages:
        bot.edit_message_reply_markup(message.chat_id, message.message_id, reply_markup=[])
    UserRegistrationMessage.query.filter_by(user_id=user_id).delete()
    db.session.commit()


def start(message):
    if isUserInDb(message['from']['username']):
        if not (checkBotRegistration(message['from']['username'], message['from']['id'], message['chat']['id'])):
            bot.send_message(message['chat']['id'],
                             "Для упрощения нашего взаимодействия через систему загрузите, пожалуйста, свою фотографию. Обратите внимание, что фотографию надо присылать в сжатом виде и не в качестве прикрепляемого документа")
            setState(message['from']['id'], 2)
        else:
            setState(message['from']['id'], 1)
            bot.send_message(message['chat']['id'],
                             "С возвращением!", reply_markup=getKeyboard(message['from']['id']))
    else:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text='Регистрация', url='http://lk.korpus.io/'))
        bot.send_message(message['chat']['id'],
                         "Кажется, Вы ещё не зарегистрированы в системе.",
                         reply_markup=markup)


@blueprint.route('/jira-bug-completed', methods=['POST'])
def process_bug_completed():
    notification = request.get_json()
    if notification.get('issue') is None or notification['issue'].get('self') is None:
        return "Wrong notification body", 400
    try:
        response = requests.get(
            f"{jira_api_url}/issue/{notification['issue']['id']}",
            params={'fields': f"description,{jira_fields.bug_creator_chat_id}"},
            auth=HTTPBasicAuth(bot_config.jira_username, bot_config.jira_token)
        )
        issue = response.json()
        bot.send_message(issue['fields'][jira_fields.bug_creator_chat_id], f"Проблема «{issue['fields']['description']}», о которой Вы заявили, была решена")
    except:
        return "Request to Jira failed", 500

    return "ok"
