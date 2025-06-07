from db import *
import telebot
from telebot import types

import matplotlib.pyplot as plt
import pandas as pd
import io

from dotenv import load_dotenv
import os

load_dotenv()

BOT_API_TOKEN = os.getenv("AutoFinancingBot_API_key")
db_expenses = os.getenv("db_expenses")
db_users = os.getenv("db_users")

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
    print("Bot started!")

    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        user_name = message.from_user.first_name
        user_surname = message.from_user.last_name
        bot.send_message(message.chat.id, f"👋 Приветствую {user_name} {user_surname}! Я бот для учёта расходов.")

        register_user_if_needed(message)
        bot.send_message(message.chat.id, f"Для того, чтобы узнать о командах бота, напишите /help")

        print("Handed: /start")

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
            print("✅ User registered:", user_fullname, user_id)
        else:
            # bot.send_message(message.chat.id,
            #                  f"👤 Пользователь уже существует: {user_fullname} ({user_id})")
            print("👤 User already exists:", user_fullname, user_id)

    @bot.message_handler(commands=['graph'])
    def send_graph(message):
        # option_msg = bot.send_message(message.chat.id, "Выберите опцию из следующего списка:")

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        graph_options = ['Статистика по категориям', 'Динамика за текущий месяц']
        for opt in graph_options:
            markup.add(opt)

        option_msg = bot.send_message(message.chat.id, "Выберите опцию из списка:", reply_markup=markup)
        bot.register_next_step_handler(option_msg, process_graph)
        print("Handed: /graph")

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
            print("Handed: /graph")

    @bot.message_handler(commands=['help'])
    def send_help(message):
        bot.send_message(message.chat.id, "Команды: /start /expense /graph")
        print("Handed: /help")

    # Step 1: /add command
    @bot.message_handler(commands=['expense'])
    def handle_add_command(message):
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
        print("Handed: /expense")

    # def process_category(message):
    #     category = message.text.strip()
    #     bot.send_message(message.chat.id, f"Категория: {category}")
    #     print("Category:", category)

    # Step 2: Handler for user reply
    def process_expense_input(message):
        try:
            if message.text.strip() == '/finish':
                bot.send_message(message.chat.id, "Расходы сохранены!")
                print("Handed: /finish")
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
            bot.send_message(message.chat.id, f"✅ Расход сохранён: {category}({subcategory}) in {store} — {amount} тг")
            print(f"✅ Расход сохранён: {category}({subcategory}) in {store} — {amount} тг")

            bot.send_message(message.chat.id, "Продолжить вводить расходы? Если нет, то напишите /finish")
            bot.register_next_step_handler(message, process_expense_input)
        except Exception as e:
            bot.send_message(message.chat.id,
                             "⚠️ Неверный формат. Пожалуйста, введите как: Категория | Подкатегория | Сумма | Краткое описание | Магазин | Дата\nПример: transport | taxi | 1300 | Work -> Home | YangexGo | ")

    try:
        bot.polling()
    except KeyboardInterrupt:
        print("Bot stopped by user.")

if __name__ == "__main__":
    start_bot()

    print("Bot stopped!")

