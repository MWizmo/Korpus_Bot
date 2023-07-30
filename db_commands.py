from models import *
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from buttons import *
from sqlalchemy import func


def isUserInDb(username):
    return User.query.filter_by(tg_nickname=username).first() or User.query.filter_by(tg_id=username).first()


def checkBotRegistration(username, tg_id, chat_id):
    if not User.query.filter_by(tg_nickname=username).first().chat_id:
        user = User.query.filter_by(tg_nickname=username).first()
        user.chat_id = chat_id
        db.session.commit()
    if not User.query.filter_by(tg_nickname=username).first().tg_id:
        user = User.query.filter_by(tg_nickname=username).first()
        user.tg_id = tg_id
        db.session.commit()
    if not User.query.filter_by(tg_nickname=username).first().photo:
        return False
    else:
        return True


def isAdmin(tg_id):
    return 1 in getStatus(tg_id)


def isTracker(tg_id):
    return 5 in getStatus(tg_id)


def isTeamLead(tg_id):
    return 4 in getStatus(tg_id)


def isChief(tg_id):
    return 2 in getStatus(tg_id)


def getKeyboard(id):
    markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    status = getStatus(id)
    if status == -1:
        markup.add('Кнопка 1', 'Кнопка 2')
    else:
        if 1 in status:
            markup.add(admin_func_btn)
        if 4 in status:
            markup.add(weekly_vote_members)
        if 2 in status or 4 in status or 5 in status:
            markup.add(voting_btn)

    return markup


def getAdminKeyboard():
    keyboard = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    keyboard.add(alert_form_btn)
    keyboard.add(alert_voting_btn)
    keyboard.add(weekly_vote_btn)
    keyboard.add(alert_results_btn)
    keyboard.add(back_btn)
    return keyboard


def getState(id):
    user = User.query.filter_by(tg_id=id).first()
    if user:
        return user.state
    else:
        return -1


def setState(id, state):
    user = User.query.filter_by(tg_id=id).first()
    if user:
        user.state = state
        db.session.commit()


def setPhoto(id, photo):
    user = User.query.filter_by(tg_id=id).first()
    if user:
        user.photo = photo
        db.session.commit()


def getStatus(id):
    user = User.query.filter_by(tg_id=int(id)).first()
    if user:
        statuses = [status.status_id for status in UserStatuses.query.filter_by(user_id=user.id).all()]
        return statuses
    else:
        return -1


def getStatusByID(id):
    user = User.query.filter_by(id=int(id)).first()
    if user:
        statuses = [status.status_id for status in UserStatuses.query.filter_by(user_id=user.id).all()]
        return statuses
    else:
        return -1


def getTgID(id):
    return User.query.filter_by(id=id).first().tg_id


def set_rang(message, bot):
    users = User.query.all()
    keyboard = InlineKeyboardMarkup()
    for user in users:
        keyboard.add(InlineKeyboardButton(text=user.name + " " + user.surname, callback_data='set_rang%' + str(user.id)))
    keyboard.add(InlineKeyboardButton(text='<Назад>', callback_data='set_rang%back'))
    bot.send_message(message.chat.id, 'Чей ранг вы хотите изменить?', reply_markup=keyboard)


def getStatusTitleByID(id):
    status = getStatusByID(id)
    if status != -1:
        statuses = [Statuses.query.filter_by(id=status_id).first().status for status_id in status]
        return ', '.join(statuses)
    else:
        return 'Unknown'


def getName(id):
    user = User.query.filter_by(id=id).first()
    return user.name + ' ' + user.surname


def setStatus(id, status):
    user = User.query.filter_by(tg_id=id).first()
    if user:
        statuses = getStatus(id)
        if not(status in statuses):
            new_status = UserStatuses(user_id=user.id, status_id=status)
            db.session.add(new_status)
            db.session.commit()


def setStatusByID(id, status):
    user = User.query.filter_by(id=id).first()
    if user:
        statuses = getStatusByID(id)
        if not(status in statuses):
            new_status = UserStatuses(user_id=user.id, status_id=status)
            db.session.add(new_status)
            db.session.commit()


def getUsersForChoosingBest(tg_id):
    users = User.query.filter_by(tg_id != tg_id).all()
    res = list()
    for user in users:
        if user.tg_id:
            res.append(user)
    return res


def get_id(tg_id):
    user = User.query.filter_by(tg_id=tg_id).first()
    if user:
        return user.id
    else:
        return -1


def getUsersSummaryFromVoting():
    cur_voting = VotingTable.query.filter_by(status='Active').first()
    if cur_voting:
        voting_id = cur_voting.id
    else:
        voting_id = VotingTable.query.filter_by(status='Finished').all()[-1].id
    users = [(user.id, user.chat_id) for user in User.query.all() if User.check_can_be_marked(user.id)]
    users_summary = {}
    for user in users:
        users_summary[user[1]] = {}
        user_res = db.session.query(func.avg(VotingInfo.mark), VotingInfo.criterion_id).outerjoin(Voting,
                                                                         Voting.id == VotingInfo.voting_id).filter(
            Voting.voting_id == voting_id, VotingInfo.cadet_id == user[0]).group_by(
            VotingInfo.criterion_id).all()
        for mark in user_res:
            if float(mark[0]) < 1.0:
                user_mark = 0
            else:
                user_mark = 1
            users_summary[user[1]][str(mark[1])] = user_mark
    return users_summary
