from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import telebot
import redis
import bot_config

app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://korpus_user:korpus_password@localhost/korpus_2023'
#app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:1@localhost/korpus_db'
db = SQLAlchemy(app)
in_memory_storage = redis.Redis(host='korpus-bot-redis', port=6379, db=0)
bot = telebot.TeleBot(bot_config.token)
#bot.set_webhook('https://bot.eos.korpus.io/tg')
jira_webhook_url = 'https://automation.atlassian.com/pro/hooks/<token_here>'
jira_api_url = 'https://korpustoken.atlassian.net/rest/api/2'
from app.routes import blueprint
app.register_blueprint(blueprint)
