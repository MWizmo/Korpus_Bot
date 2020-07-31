from app import bot
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
        elif text == weekly_vote_btn:
            users = User.query.all()
            for user in users:
                try:
                    status = getStatus(user.tg_id)
                    if 2 in status or 4 in status or 5 in status:
                        bot.send_message(user.chat_id, 'Привет! Сегодня оцениваем какие-то команды?')
                except:
                    pass
            bot.send_message(chat_id, 'Оповещения отправлены')
        elif text == voting_btn:
            today = datetime.date(datetime.datetime.now().year, datetime.datetime.now().month,
                                  datetime.datetime.now().day)
            teams = Teams.query.filter_by(type=1).all()
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
        elif text == weekly_vote_members:
            cadet_id = get_id(user_id)
            teams = Membership.query.filter_by(user_id=cadet_id).all()
            tid = [t.team_id for t in teams if Teams.query.filter_by(id=t.team_id).first().type == 1][0]
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
        elif text == alert_form_btn and isAdmin(user_id):
            cadets = [user for user in User.query.all() if User.check_can_be_marked(user.id)]
            user_names = list()
            month = datetime.datetime.now().month
            for user in cadets:
                if len(Questionnaire.query.filter(Questionnaire.user_id == user.id,
                                                  func.month(Questionnaire.date) == month).all()) + len(
                    Questionnaire.query.filter(Questionnaire.user_id == user.id,
                                               func.month(Questionnaire.date) == month - 1).all()) < 2:
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
                                           func.month(Voting.date) == month,
                                           Voting.axis_id == 1).all()) < marked_teams_num:
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
                                           func.month(Voting.date) == month,
                                           Voting.axis_id == 2).all()) < marked_teams_num:
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
        f = open(r'/home/snapper/KorpusToken/app/static/user_photos/user' + str(get_id(message['from']['id'])) + '.jpg',
                 "wb")
        ufr = requests.get(photo_url)
        f.write(ufr.content)
        f.close()
        setPhoto(_id, photo_url)
        # bot.send_photo(message['chat']['id'], photo)
        bot.send_message(message['chat']['id'], 'Добро пожаловать!', reply_markup=getKeyboard(message['from']['id']))
        setState(message['from']['id'], 1)


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
            users = [user for user in User.query.all() if (User.check_expert(user.id) or User.check_tracker(user.id))]
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
            bot.send_message(chat_id, 'Главное меню', reply_markup=getKeyboard(user_id))
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
                teams = Teams.query.filter_by(type=1).all()
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
                teams = Teams.query.filter_by(type=1).all()
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


def start(message):
    if isUserInDb(message['from']['username']):
        if not (checkBotRegistration(message['from']['username'], message['from']['id'], message['chat']['id'])):
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
