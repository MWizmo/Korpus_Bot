FROM python:3.11

WORKDIR /usr/src/app

RUN pip install sqlalchemy flask Flask-SQLAlchemy telebot pymysql cryptography redis web3

COPY . .

EXPOSE 5050

CMD [ "python", "./wsgi.py" ]