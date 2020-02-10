from models import *
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from buttons import *


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


def getKeyboard(id):
    markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    status = getStatus(id)
    if status == -1:
        markup.add('Кнопка 1', 'Кнопка 2')
    elif 1 in status:
        markup.add(admin_func_btn)
    return markup


def getAdminKeyboard():
    keyboard = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    keyboard.add(alert_form_btn)
    keyboard.add(alert_voting_btn)
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

