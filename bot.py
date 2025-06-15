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

db_data = os.getenv("db_data")

admin_user_id = os.getenv("admin_user_id")

income_categories = {
    "Bills & Charges": ["Bonus Back", "Deposit", "Refund"],
    "Correction": ["Correction"],
    "Gifts": ["Gifts"],
    "Salary": ["Monthly Share", "Salary"]
}

expense_categories = {
    "Auto": ["Bus", "Taxi", "Metro", "Jet"],
    "Bills & Charges": ["Commission", "Debt", "Monthly Share", "Monthly Pay", "Refund"],
    "Correction": ["Correction"],
    "Eating Out": ["Bar", "Cafe", "Diner", "FastFood", "Order"],
    "Education": ["Edu Stuffs", "802.11 & calls, sms", "Printing", "Subscription"],
    "Entertainment": ["Cinema", "Games", "Guitar", "Partying", "Poker", "Subscription", "Table Tennis"],
    "Gifts": ["Books", "Cakes", "🌹Flowers🪻🌷"],
    "Groceries": ["!MyPurchases", "Baking", "Beverage", "Cooked", "Foodstuffs", "Fruits & Vegetables", "Items", "Meat",
                  "Milk", "Nuts", "Sauce & Spices", "Sushi", "Sweets, candies, cakes & snacks"],
    "Health & Fitness": ["Diet", "Sport"],
    "Kids": ["Toys", "Books"],
    "Personal Care": ["Barvershop", "Communication", "Finance", "Health", "Music", "Sport"],
    "Shopping": ["Books", "Clothes", "Gadgets", "Sport", "Tea", "Other"],
    "Travel": ["Airline", "Train"]}

# Хранилище состояний и данных пользователей
user_state_income = {}
user_state_expense = {}

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

def start_bot():
    bot = telebot.TeleBot(BOT_API_TOKEN)

    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        user_name = message.from_user.first_name
        user_surname = message.from_user.last_name
        user_id = str(message.from_user.id).strip()
        if user_id != admin_user_id:
            bot.send_message(message.chat.id, f"👋 Приветствую {user_name} {user_surname}! Я бот для учёта расходов.")
        else:
            bot.send_message(message.chat.id, f"👋 Приветствую создатель!")
            bot.send_message(message.chat.id, f"Введите /daily_deposit для учета ежедневных накоплений.")

        register_user_if_needed(message)

        logging.info(f"/start от {user_name} {user_surname}")
        # print("Handed: /start")

    @bot.message_handler(commands=['daily_deposit'])
    def send_daily_deposit_by_admin(message):
        user_id = str(message.from_user.id).strip()

        if user_id == admin_user_id:
            logging.info(f"/daily_deposit by Admin")

            date_deposit = bot.send_message(message.from_user.id, "Введите дату (DD.MM.YYYY):")
            bot.register_next_step_handler(date_deposit, date_daily_deposit_by_admin)
        else:
            bot.send_message(message.chat.id, "У вас нет прав для этой команды.")
            logging.warning(f"/daily_deposit by {message.from_user.id} - not Admin. Permission denied.")

    def date_daily_deposit_by_admin(message):
        date = message.text.strip()
        if date is None or date.strip() == '':
            date = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")

        conn = sqlite3.connect(db_data)
        cursor = conn.cursor()
        cursor.execute("""
                        INSERT INTO INCOMES (user_id, category, subcategory, amount, description, date)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """, (admin_user_id, "Bills & Charges", "Deposit", 1722.60, "Ежедневный депозит", date)
                       )
        conn.commit()
        conn.close()

        bot.delete_message(message.chat.id, message.message_id-1)
        bot.delete_message(message.chat.id, message.message_id)
        bot.send_message(message.chat.id, "✅ Ежедневный депозит успешно добавлен!")

    def register_user_if_needed(message):
        user_id = int(message.from_user.id)
        user_fullname = message.from_user.first_name + ' ' + message.from_user.last_name
        register_date = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")

        conn = sqlite3.connect(db_data)
        cursor = conn.cursor()

        # Check if user exists
        cursor.execute("SELECT * FROM USERS WHERE user_id = ?", (user_id,))
        user_exist = cursor.fetchone()

        if user_exist is None:
            cursor.execute("""
                                INSERT INTO USERS (user_id, user_fullname, register_date)
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

        markup = types.InlineKeyboardMarkup(row_width=2)
        buttons = []
        graph_options = ['Статистика по категориям', 'Динамика за текущий месяц']
        for opt in graph_options:
            btn = types.InlineKeyboardButton(text=opt, callback_data=f"graph:{opt}")
            buttons.append(btn)
        markup.add(*buttons)

        option_msg = bot.send_message(message.chat.id, "Выберите опцию из списка:", reply_markup=markup)

        logging.info(f"/graph от {message.from_user.first_name} {message.from_user.last_name}")
        # print("Handed: /graph")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("graph:"))
    def process_graph(message):
        graph_type = message.data.split(":")[1].strip()

        user_id = message.from_user.id
        chat_id = message.chat.id

        conn = sqlite3.connect(db_data)
        # cursor = conn.cursor()
        df = pd.read_sql_query(
            f"SELECT category, subcategory, amount, description, store, date FROM EXPENSES WHERE user_id = {user_id}",
            conn)

        for label in ['category', 'subcategory', 'description', 'store', 'date']:
            df[label] = df[label].apply(lambda x: x.strip())
        # print(df)

        if graph_type == 'Статистика по категориям':
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
        elif graph_type == 'Динамика за текущий месяц':
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

    @bot.message_handler(commands=['expense'])
    def handle_expense_command(message):
        logging.info(f"/expense от {message.from_user.first_name} {message.from_user.last_name}")

        user_state_expense[message.chat.id] = {'step': 'category'}

        markup_category = types.InlineKeyboardMarkup(row_width=3)

        category_buttons = []
        for category in expense_categories.keys():
            button = types.InlineKeyboardButton(text=category, callback_data=f"expense_cat:{category}")
            category_buttons.append(button)

        markup_category.add(*category_buttons)

        bot.send_message(message.chat.id,
                         "Выберите категорию расхода или введите все данные следующим образом:\n`Категория* | Подкатегория* | Сумма* | Описание | Магазин | Дата (DD.MM.YYYY)`",
                         reply_markup=markup_category,
                         parse_mode="Markdown"
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("expense_cat:"))
    def handle_expense_category_callback(call):
        chat_id = call.message.chat.id
        selected_category = call.data.split(":")[1]
        state = user_state_expense[chat_id]
        state['category'] = selected_category

        bot.answer_callback_query(call.id)

        markup_subcategory = types.InlineKeyboardMarkup(row_width=3)
        buttons = []
        for subcategory in expense_categories[selected_category]:
            button = types.InlineKeyboardButton(text=subcategory, callback_data=f"expense_subcat:{subcategory}")
            buttons.append(button)
        markup_subcategory.add(*buttons)

        bot.edit_message_text(chat_id=call.message.chat.id,
                              message_id=call.message.message_id,
                              text=f"Категория выбрана: {selected_category}\nТеперь выберите подкатегорию:",
                              reply_markup=markup_subcategory)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("expense_subcat:"))
    def handle_expense_subcategory_callback(call):
        chat_id = call.message.chat.id
        selected_subcategory = call.data.split(":")[1]
        state = user_state_expense[chat_id]

        if chat_id in user_state_expense:
            state['subcategory'] = selected_subcategory
            state['step'] = 'amount_description_shop_date'

            bot.answer_callback_query(call.id)
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=f"Категория выбрана: {state['category']}\nПодкатегория выбрана: {selected_subcategory}\nТеперь введите:\n`Сумма* | Описание | Магазин | Дата (DD.MM.YYYY)`",
                parse_mode="Markdown"
            )

    @bot.message_handler(func=lambda message: message.chat.id in user_state_expense)
    def handle_expense_steps(message):
        chat_id = message.chat.id
        state = user_state_expense[chat_id]
        step = state['step']

        if step == 'category':
            selected_category = message.text.strip()
            if selected_category not in expense_categories.keys():
                user_state_expense.pop(chat_id)

                logging.info(f"Handed oneline expense by {message.from_user.first_name} {message.from_user.last_name}")
                process_expense_input_oneline(message)
            else:
                state['category'] = selected_category
                state['step'] = 'subcategory'

                markup_subcategory = types.InlineKeyboardMarkup(row_width=3)
                buttons = []
                for subcategory in expense_categories[selected_category]:
                    btn = types.InlineKeyboardButton(text=subcategory, callback_data=f"expense_subcat:{subcategory}")
                    buttons.append(btn)
                markup_subcategory.add(*buttons)

                bot.send_message(chat_id, "Выберите подкатегорию расхода:", reply_markup=markup_subcategory)
        elif step == 'subcategory':
            selected_subcategory = message.text.strip()
            state['subcategory'] = selected_subcategory
            state['step'] = 'amount_description_shop_date'

            bot.send_message(chat_id,
                             f"Введите `Сумма* | Описание | Магазин | Дата в формате DD.MM.YYYY`",
                            parse_mode="Markdown")
        elif step == 'amount_description_shop_date':
            try:
                amount, description, store, date = message.text.split('|')

                amount = float(amount.strip())
                description = description.strip()
                store = store.strip()
                if date is None or date.strip() == '':
                    date = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")

                chat_id = message.chat.id
                user_id = message.from_user.id
                category = state['category']
                subcategory = state['subcategory']

                # Save to DB
                conn = sqlite3.connect(db_data)
                cursor = conn.cursor()
                cursor.execute("""
                                    INSERT INTO EXPENSES (user_id, category, subcategory, amount, description, store, date)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)
                                """, (user_id, category, subcategory, amount, description, store, date))
                conn.commit()
                conn.close()

                user_state_expense.pop(chat_id)
                bot.delete_message(chat_id, message.message_id-1)
                bot.delete_message(chat_id, message.message_id)

                bot.send_message(message.chat.id,
                                 f"✅ Расход сохранён: {category} ({subcategory}) in {store} — {amount} тг")
                logging.info(
                    f"Расход сохранён: {category} ({subcategory}) in {store} — {amount} тг от {message.from_user.first_name} {message.from_user.last_name}")
            except Exception as e:
                logging.warning(f"⚠️ Задан неверный формат \expense от {message.from_user.first_name} {message.from_user.last_name}")
                bot.send_message(chat_id,
                                 "️ Неверный формат. Пожалуйста, введите как: `Категория* | Подкатегория* | Сумма* | Краткое описание | Магазин | Дата`\nПример: Auto | Taxi | 1300 | Work -> Home | YangexGo | ",
                                 parse_mode="Markdown")

    def process_expense_input_oneline(message):
        try:
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
            conn = sqlite3.connect(db_data)
            cursor = conn.cursor()
            cursor.execute("""
                    INSERT INTO EXPENSES (user_id, category, subcategory, amount, description, store, date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (user_id, category, subcategory, amount, description, store, date))
            conn.commit()
            conn.close()

            bot.delete_message(message.chat.id, message.message_id-1)
            bot.delete_message(message.chat.id, message.message_id)

            bot.send_message(message.chat.id, f"✅ Расход сохранён: {category} ({subcategory}) in {store} — {amount} тг")
            logging.info(f"Расход сохранён: {category} ({subcategory}) in {store} — {amount} тг от {message.from_user.first_name} {message.from_user.last_name}")

            # bot.send_message(message.chat.id, "Продолжить вводить расходы? Если нет, то напишите /finish")
            # bot.register_next_step_handler(message, process_expense_input_oneline)
        except Exception as e:
            logging.warning(f"⚠️ Задан неверный формат \expense от {message.from_user.first_name} {message.from_user.last_name}")
            bot.send_message(message.chat.id,
                             "⚠️ Неверный формат. Пожалуйста, введите как: `Категория* | Подкатегория* | Сумма* | Описание | Магазин | Дата`\nПример: transport | taxi | 1300 | Work -> Home | YangexGo | ",
                             parse_mode="Markdown")

    @bot.message_handler(commands=['income'])
    def handle_income_command(message):
        logging.info(f"/income от {message.from_user.first_name} {message.from_user.last_name}")

        user_state_income[message.chat.id] = {'step': 'category'}

        markup_category = types.InlineKeyboardMarkup(row_width=3)

        category_buttons = []
        for category in income_categories.keys():
            button = types.InlineKeyboardButton(text=category, callback_data=f"income_cat:{category}")
            category_buttons.append(button)

        markup_category.add(*category_buttons)

        bot.send_message(message.chat.id,
                         "Выберите категорию дохода или введите все данные следующим образом:\n`Категория* | Подкатегория* | Сумма* | Краткое описание | Дата (DD.MM.YYYY)`",
                         reply_markup=markup_category,
                         parse_mode="Markdown"
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("income_cat:"))
    def handle_income_category_callback(call):
        chat_id = call.message.chat.id
        selected_category = call.data.split(":")[1]
        state = user_state_income[chat_id]
        state['category'] = selected_category
        state['step'] = 'subcategory'

        bot.answer_callback_query(call.id)

        markup_subcategory = types.InlineKeyboardMarkup(row_width=3)
        buttons = []
        for subcategory in income_categories[selected_category]:
            button = types.InlineKeyboardButton(text=subcategory, callback_data=f"income_subcat:{subcategory}")
            buttons.append(button)
        markup_subcategory.add(*buttons)

        bot.edit_message_text(chat_id=call.message.chat.id,
                              message_id=call.message.message_id,
                              text=f"Категория выбрана: {selected_category}\nТеперь выберите подкатегорию:",
                              reply_markup=markup_subcategory)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("income_subcat:"))
    def handle_income_subcategory_callback(call):
        chat_id = call.message.chat.id
        selected_subcategory = call.data.split(":")[1]
        state = user_state_income[chat_id]

        if chat_id in user_state_income:
            state['subcategory'] = selected_subcategory
            state['step'] = 'amount_description_date'

            bot.answer_callback_query(call.id)
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=f"Категория выбрана: {state['category']}\nПодкатегория выбрана: {selected_subcategory}\nТеперь введите:\n`Сумма* | Описание | Дата (можно пропустить)`",
                parse_mode="Markdown"
            )

    @bot.message_handler(func=lambda message: message.chat.id in user_state_income)
    def handle_income_steps(message):
        chat_id = message.chat.id
        state = user_state_income[chat_id]
        step = state['step']

        if step == 'category':
            selected_category = message.text.strip()
            if selected_category not in income_categories.keys():
                user_state_income.pop(chat_id)

                logging.info(
                    f"Handed oneline income by {message.from_user.first_name} {message.from_user.last_name}")
                process_income_input_oneline(message)
            else:
                state['category'] = selected_category
                state['step'] = 'subcategory'


                markup_subcategory = types.InlineKeyboardMarkup(row_width=3)
                buttons = []
                for subcategory in income_categories[selected_category]:
                    btn = types.InlineKeyboardButton(text=subcategory, callback_data=f"income_subcat:{subcategory}")
                    buttons.append(btn)
                markup_subcategory.add(*buttons)

                bot.send_message(chat_id, "Выберите подкатегорию дохода:", reply_markup=markup_subcategory)
        elif step == 'subcategory':
            selected_subcategory = message.text.strip()
            state['subcategory'] = selected_subcategory
            state['step'] = 'amount_description_date'

            bot.send_message(chat_id,
                             f"Введите `Сумма* | Описание | Дата (DD.MM.YYYY))",
                             parse_mode="Markdown")
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
                conn = sqlite3.connect(db_data)
                cursor = conn.cursor()
                cursor.execute("""
                                INSERT INTO INCOMES (user_id, category, subcategory, amount, description, date)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (user_id, category, subcategory, amount, description, date))
                conn.commit()
                conn.close()

                user_state_income.pop(chat_id)
                bot.delete_message(chat_id, message.message_id-1)
                bot.delete_message(chat_id, message.message_id)

                # Send success message
                bot.send_message(chat_id,
                                 f"✅ Доход сохранён: {category} ({subcategory}) — {amount} тг")
                logging.info(
                    f"✅ Доход сохранён: {category} ({subcategory}) — {amount} тг (income) от {message.from_user.first_name} {message.from_user.last_name}")
                # print(f"✅ Доход сохранён: {category} ({subcategory}) — {amount} тг")
            except Exception as e:
                logging.warning(f"⚠️ Задан неверный формат \income от {message.from_user.first_name} {message.from_user.last_name}")
                bot.send_message(chat_id,
                                 "⚠️ Неверный формат. Пожалуйста, введите как: `Сумма* | Описание | Дата`\nПример: 20000 | Днюха | 28.02.2025",
                                 parse_mode="Markdown")

    def process_income_input_oneline(message):
        try:
            parts = message.text.strip().split('|')

            if len(parts) == 5:
                category, subcategory, amount, description, date = parts

            if date is None or date.strip() == '':
                date = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")

            category = category.strip()
            subcategory = subcategory.strip()
            amount = float(amount.strip())
            description = description.strip()
            date = date.strip()

            user_id = message.from_user.id

            # Save to DB
            conn = sqlite3.connect(db_data)
            cursor = conn.cursor()
            cursor.execute("""
                    INSERT INTO INCOMES (user_id, category, subcategory, amount, description, date)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, category, subcategory, amount, description, date))
            conn.commit()
            conn.close()

            bot.delete_message(message.chat.id, message.message_id - 1)
            bot.delete_message(message.chat.id, message.message_id)

            bot.send_message(message.chat.id, f"✅ Доход сохранён: {category} ({subcategory}) — {amount} тг")
            logging.info(
                f"Доход сохранён: {category} ({subcategory}) — {amount} тг от {message.from_user.first_name} {message.from_user.last_name}")
            # print(f"✅ Расход сохранён: {category} ({subcategory}) in {store} — {amount} тг")

            # bot.send_message(message.chat.id, "Продолжить вводить доходы? Если нет, то напишите /finish")
            # bot.register_next_step_handler(message, process_income_input_oneline)
        except Exception as e:
            logging.warning(f"⚠️ Задан неверный формат \income от {message.from_user.first_name} {message.from_user.last_name}")
            bot.send_message(message.chat.id,
                             f"⚠️ Неверный формат. Пожалуйста, введите как: `Категория* | Подкатегория* | Сумма* | Краткое описание | Дата`\nПример: Bills & Charges | Bonus Back | 5000 | Home Credit Bank | 01.07.2025",
                             parse_mode="Markdown")

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

    bot.polling()
    #     print("Bot stopped by user.")

if __name__ == "__main__":
    logging.info("The bot has been launched!")
    start_bot()
    logging.info("Bot stopped!")

