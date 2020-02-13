from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import telebot
import bot_config

app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://korpus_user:korpus_password@localhost/korpus_db'
db = SQLAlchemy(app)
bot = telebot.TeleBot(bot_config.token)
bot.set_webhook('https://bot.eos.korpus.io/tg')
from app.routes import blueprint
app.register_blueprint(blueprint)
