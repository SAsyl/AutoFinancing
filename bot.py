from db import *
import telebot
from telebot import types

import matplotlib.pyplot as plt
import pandas as pd
import io

from dotenv import load_dotenv
import os
import logging

import requests

load_dotenv()

BOT_API_TOKEN = os.getenv("AutoFinancingBot_API_key")

WEATHER_API_TOKEN = os.getenv("Weather_API_key")

db_expenses = os.getenv("db_expenses")
db_incomes = os.getenv("db_incomes")
db_users = os.getenv("db_users")

income_categories = {"Bills & Charges": ["Bonus Back", "Deposit", "Refund"],
                     "Correction": ["Correction"],
                     "Gifts": ["Gifts"],
                     "Salary": ["Monthly Share", "Salary"]}

# Хранилище состояний и данных пользователей
user_state = {}
# Возможные этапы
STEPS_INCOME = ['category', 'subcategory', 'amount_description_date']

if not os.path.exists("logs"):
    os.mkdir("logs")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def manual_insert():
    user_id = input("User ID: ")
    category = input("Category: ")
    subcategory = input("Subcategory: ")
    amount = input("Amount: ")
    description = input("Description: ")
    store = input("Store: ")
    date = input("Date: ")

    add_expense(user_id, category, subcategory, amount, description, store, date=None)
    print("Complete!")

def start_bot():
    bot = telebot.TeleBot(BOT_API_TOKEN)
    # print("Bot started!")

    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        user_name = message.from_user.first_name
        user_surname = message.from_user.last_name
        user_id = message.from_user.id
        bot.send_message(message.chat.id, f"👋 Приветствую {user_name} {user_surname}! Я бот для учёта расходов.")

        register_user_if_needed(message)
        bot.send_message(message.chat.id, f"Для того, чтобы узнать о командах бота, напишите /help")

        logging.info(f"/start от {user_name} {user_surname}")
        # print("Handed: /start")

    def register_user_if_needed(message):
        user_id = int(message.from_user.id)
        user_fullname = message.from_user.first_name + ' ' + message.from_user.last_name
        register_date = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")

        conn = sqlite3.connect(db_users)
        cursor = conn.cursor()

        # Check if user exists
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user_exist = cursor.fetchone()

        if user_exist is None:
            cursor.execute("""
                                INSERT INTO users (user_id, user_fullname, register_date)
                                VALUES (?, ?, ?)
                            """, (user_id, user_fullname, register_date))
            conn.commit()
            conn.close()

            # bot.send_message(message.chat.id,
            #                  f"✅ Пользователь {user_fullname} зарегистрирован!")
            logging.info(f"✅ User registered: {user_fullname}, {user_id}")
            # print("✅ User registered:", user_fullname, user_id)
        else:
            # bot.send_message(message.chat.id,
            #                  f"👤 Пользователь уже существует: {user_fullname} ({user_id})")
            logging.info(f" User already exists: {user_fullname}, {user_id}")
            # print("👤 User already exists:", user_fullname, user_id)

    @bot.message_handler(commands=['graph'])
    def send_graph(message):
        # option_msg = bot.send_message(message.chat.id, "Выберите опцию из следующего списка:")

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        graph_options = ['Статистика по категориям', 'Динамика за текущий месяц']
        for opt in graph_options:
            markup.add(opt)

        option_msg = bot.send_message(message.chat.id, "Выберите опцию из списка:", reply_markup=markup)
        bot.register_next_step_handler(option_msg, process_graph)

        logging.info(f"/graph от {message.from_user.first_name} {message.from_user.last_name}")
        # print("Handed: /graph")

    def process_graph(message):
        user_id = message.from_user.id
        chat_id = message.chat.id

        conn = sqlite3.connect(db_expenses)
        cursor = conn.cursor()

        df = pd.read_sql_query(
            f"SELECT category, subcategory, amount, description, store, date FROM expenses WHERE user_id = {user_id}",
            conn)

        for label in ['category', 'subcategory', 'description', 'store', 'date']:
            df[label] = df[label].apply(lambda x: x.strip())
        # print(df)

        if message.text == 'Статистика по категориям':
            grouped_by_category = df.groupby('category')['amount'].sum().reset_index()
            # print(grouped_by_category)

            except_salary = grouped_by_category[grouped_by_category['category'] != 'salary']

            plt.figure(figsize=(6, 6))
            plt.pie(
                except_salary['amount'],
                labels=except_salary['category'],
                autopct='%1.1f%%',
                startangle=140
            )
            plt.title("Распределение расходов по категориям за все время")
            plt.axis('equal')  # Круг
            plt.tight_layout()

            buffer = io.BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            plt.close()

            bot.send_photo(chat_id, photo=buffer)
        elif message.text == 'Динамика за текущий месяц':
            today = datetime.date.today()
            # print(today)
            df['date'] = df['date'].apply(lambda x: datetime.datetime.strptime(x.split(' ')[0], "%d.%m.%Y").date())
            df['date'] = pd.to_datetime(df['date'])
            # print(df.info())

            df_curr_month = df[
                (df['date'].dt.year == today.year) &
                (df['date'].dt.month == today.month)
            ]
            daily_spending = df_curr_month.groupby(df_curr_month['date'].dt.day)['amount'].sum()
            # print(daily_spending)

            plt.figure(figsize=(8, 5))
            plt.plot(daily_spending.index, daily_spending.values, marker='o', linestyle='-', color='blue')

            plt.title(f"Расходы за {today.strftime('%B %Y')}")
            plt.xlabel("День месяца")
            plt.ylabel("Сумма расходов (тг)")
            plt.grid(True)
            plt.tight_layout()

            buffer = io.BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            plt.close()

            bot.send_photo(chat_id, buffer)
        else:
            logging.warning(f"Unexpected /graph option: {message.text}")
            # print("Handed: /graph")

    @bot.message_handler(commands=['help'])
    def send_help(message):
        bot.send_message(message.chat.id, "Команды: /start /expense /income /graph /current_weather /forecast_weather")
        logging.info(f"/help от {message.from_user.first_name} {message.from_user.last_name}")
        # print("Handed: /help")

    # Step 1: /add command
    @bot.message_handler(commands=['expense'])
    def handle_expense_command(message):
        expenses_msg = bot.send_message(message.chat.id, "Введите расходы в формате:\nКатегория | Подкатегория | Сумма | Краткое описание | Магазин | Дата (если сегодня, то можно пропустить, иначе в формате DD.MM.YYYY (HH:MM:SS))")
        # expenses_msg = bot.send_message(message.chat.id, "Или же выберите категорию из следующего списка:")
        #
        # markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        # categories = ['Auto', 'Travel', 'Bills & Charges', 'Eating Out', 'Education', 'Entertainment', 'Gifts',
        #               'Groceries', 'Health & Fitness', 'Kids', 'Personal Care', 'Salary', 'Shopping', 'Other']
        # for cat in categories:
        #     markup.add(cat)
        #
        # category_msg = bot.send_message(message.chat.id, "Выберите категорию расхода:", reply_markup=markup)
        # bot.register_next_step_handler(category_msg, process_category)

        bot.register_next_step_handler(expenses_msg, process_expense_input)
        logging.info(f"/expense от {message.from_user.first_name} {message.from_user.last_name}")
        # print("Handed: /expense")

    # def process_category(message):
    #     category = message.text.strip()
    #     bot.send_message(message.chat.id, f"Категория: {category}")
    #     print("Category:", category)

    # Step 2: Handler for user reply
    def process_expense_input(message):
        try:
            if message.text.strip() == '/finish':
                bot.send_message(message.chat.id, "Расходы сохранены!")
                logging.info(f"/finish (expense) от {message.from_user.first_name} {message.from_user.last_name}")
                # print("Handed: /finish")
                return

            parts = message.text.strip().lower().split('|')
            if len(parts) == 6:
                category, subcategory, amount, description, store, date = parts

            if date is None or date == '':
                date = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")

            category = category.strip()
            subcategory = subcategory.strip()
            amount = amount.strip()
            description = description.strip()
            store = store.strip()
            date = date.strip()

            amount = float(amount)
            user_id = message.from_user.id

            # Save to DB
            conn = sqlite3.connect(db_expenses)
            cursor = conn.cursor()
            cursor.execute("""
                    INSERT INTO expenses (user_id, category, subcategory, amount, description, store, date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (user_id, category, subcategory, amount, description, store, date))
            conn.commit()
            conn.close()

            # Send success message
            bot.send_message(message.chat.id, f"✅ Расход сохранён: {category} ({subcategory}) in {store} — {amount} тг")
            logging.info(f"Расход сохранён: {category} ({subcategory}) in {store} — {amount} тг от {message.from_user.first_name} {message.from_user.last_name}")
            # print(f"✅ Расход сохранён: {category} ({subcategory}) in {store} — {amount} тг")

            bot.send_message(message.chat.id, "Продолжить вводить расходы? Если нет, то напишите /finish")
            bot.register_next_step_handler(message, process_expense_input)
        except Exception as e:
            logging.warning(f"⚠️ Задан неверный формат \expense от {message.from_user.first_name} {message.from_user.last_name}")
            bot.send_message(message.chat.id,
                             "⚠️ Неверный формат. Пожалуйста, введите как: Категория | Подкатегория | Сумма | Краткое описание | Магазин | Дата\nПример: transport | taxi | 1300 | Work -> Home | YangexGo | ")

    # Step 1: /add command
    @bot.message_handler(commands=['income'])
    def handle_income_command(message):
        income_data = []
        logging.info(f"/income от {message.from_user.first_name} {message.from_user.last_name}")

        user_state[message.chat.id] = {'step': 'category'}

        # bot.send_message(message.chat.id,
        #                                 "Введите доход в формате:\nКатегория | Подкатегория | Сумма | Краткое описание | Дата (если сегодня, то можно пропустить, иначе в формате DD.MM.YYYY (HH:MM:SS))")
        # income_msg = bot.send_message(message.chat.id, "Выберите категорию из следующего списка:")

        markup_category = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for category in income_categories.keys():
            markup_category.add(category)

        bot.send_message(message.chat.id, "Выберите категорию дохода:", reply_markup=markup_category)

    @bot.message_handler(func=lambda message: message.chat.id in user_state)
    def handle_income_steps(message):
        chat_id = message.chat.id
        state = user_state[chat_id]
        step = state['step']

        if step == 'category':
            selected_category = message.text.strip()
            state['category'] = selected_category
            state['step'] = 'subcategory'

            markup_subcategory = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            for subcategory in income_categories[selected_category]:
                markup_subcategory.add(subcategory)

            bot.send_message(chat_id, "Выберите подкатегорию дохода:", reply_markup=markup_subcategory)
        elif step == 'subcategory':
            selected_subcategory = message.text.strip()
            state['subcategory'] = selected_subcategory
            state['step'] = 'amount_description_date'

            bot.send_message(chat_id, f"Введите Сумма | Краткое описание | Дата в формате DD.MM.YYYY (если сегодня, то можно пропустить)")
        elif step == 'amount_description_date':
            try:
                amount, description, date = message.text.split('|')

                amount = float(amount.strip())
                description = description.strip()
                if date is None or date.strip() == '':
                    date = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")

                chat_id = message.chat.id
                user_id = message.from_user.id
                category = state['category']
                subcategory = state['subcategory']

                # Save to DB
                conn = sqlite3.connect(db_incomes)
                cursor = conn.cursor()
                cursor.execute("""
                                INSERT INTO incomes (user_id, category, subcategory, amount, description, date)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (user_id, category, subcategory, amount, description, date))
                conn.commit()
                conn.close()

                user_state.pop(chat_id)

                # Send success message
                bot.send_message(chat_id,
                                 f"✅ Доход сохранён: {category} ({subcategory}) — {amount} тг")
                logging.info(
                    f"✅ Доход сохранён: {category} ({subcategory}) — {amount} тг (income) от {message.from_user.first_name} {message.from_user.last_name}")
                # print(f"✅ Доход сохранён: {category} ({subcategory}) — {amount} тг")
            except Exception as e:
                logging.warning(f"⚠️ Задан неверный формат \income от {message.from_user.first_name} {message.from_user.last_name}")
                bot.send_message(chat_id,
                                 "⚠️ Неверный формат. Пожалуйста, введите как: Категория | Подкатегория | Сумма | Краткое описание | Дата\nПример: 20000 | Днюха | 28.02.2003 ")

    @bot.message_handler(commands=['current_weather'])
    def send_current_weather(message):
        city = 'Astana'
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_TOKEN}&units=metric&lang=ru"

        response = requests.get(url)
        data = response.json()

        if response.status_code == 200:
            temp = data['main']['temp']
            weather_desc = data['weather'][0]['description']
            wind_speed = data['wind']['speed']

            bot.send_message(message.chat.id, f"🌤️ Погода в Астане сейчас:\nТемпература: {temp}°C\nОписание: {weather_desc}\nВетер: {wind_speed} м/с")
            logging.info(f"/current_weather от {message.from_user.first_name} {message.from_user.last_name}")
        else:
            logging.warning(f"⚠️ Ошибка при получении данных о погоде от {message.from_user.first_name} {message.from_user.last_name}")

    @bot.message_handler(commands=['forecast_weather'])
    def send_forecast_weather(message):
        city = 'Astana'
        url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={WEATHER_API_TOKEN}&units=metric&lang=ru"

        response = requests.get(url)
        data = response.json()

        if response.status_code == 200:
            day_count = 0
            last_date = ""

            for entry in data['list']:
                dt_txt = entry['dt_txt']  # формат: '2025-06-06 15:00:00'
                date_str = dt_txt.split(" ")[0]
                time_str = dt_txt.split(" ")[1][:5]

                # Печатаем только одну запись в день (например, в 12:00)
                if time_str.startswith("12") and date_str != last_date:
                    last_date = date_str
                    day_count += 1

                    temp = entry['main']['temp']
                    weather = entry['weather'][0]['description']
                    wind = entry['wind']['speed']

                    date_formatted = datetime.datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")
                    bot.send_message(message.chat.id, f"📅 {date_formatted}: {weather.capitalize()}, 🌡{temp}°C, 💨 ветер {wind} м/с")
                    # print(f"📅 {date_formatted}: {weather.capitalize()}, 🌡 {temp}°C, 💨 ветер {wind} м/с")

                if day_count == 3:
                    break

            logging.info(f"/forecast_weather от {message.from_user.first_name} {message.from_user.last_name}")
        else:
            logging.warning(
                f"⚠️ Ошибка при получении данных о погоде от {message.from_user.first_name} {message.from_user.last_name}")

    # try:
    bot.polling()
    # except KeyboardInterrupt:
    #     print("Bot stopped by user.")

if __name__ == "__main__":
    logging.info("The bot has been launched!")
    start_bot()
    logging.info("Bot stopped!")

    # print("Bot stopped!")

