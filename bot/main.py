import logging
from datetime import datetime, timedelta

import pytz
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import navigation
from conf import API_TOKEN, CREDENTIALS_FILE
from db import Database
from parsering import parse_google_sheet

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

db = Database('database.db')
db.create_tables()

# region Scheduler
scheduler = AsyncIOScheduler(timezone=pytz.timezone("Europe/Moscow"))


def schedule_notifications():
    scheduler.add_job(check_for_notifications, trigger='interval', minutes=0.1)
    scheduler.start()
    logging.info("Notifications scheduled")


async def send_notification(user_id, message):
    await bot.send_message(user_id, message)
    logging.info(f"Notification sent to user {user_id}: {message}")


async def check_for_notifications():
    logging.info("Checking for notifications...")
    now = datetime.now(pytz.timezone("Europe/Moscow"))
    users = db.get_all_users()
    logging.debug(f"Found {len(users)} users")

    weekday_map = {
        "Понедельник": 0,
        "Вторник": 1,
        "Среда": 2,
        "Четверг": 3,
        "Пятница": 4,
        "Суббота": 5,
        "Воскресение": 6
    }

    for user in users:
        user_id = user['user_id']
        appointments = db.get_user_appointments(user_id)
        logging.debug(f"Found {len(appointments)} appointments for user {user_id}")

        for appointment in appointments:
            course_id = appointment['course_id']
            appointment_day = weekday_map[appointment['weekday']]
            appointment_time = datetime.strptime(appointment['time'], '%H:%M').time()
            appointment_date = now.date() + timedelta(days=(appointment_day - now.weekday() + 7) % 7)
            appointment_datetime = datetime.combine(appointment_date, appointment_time)
            appointment_datetime = pytz.timezone("Europe/Moscow").localize(appointment_datetime)
            time_diff = (appointment_datetime - now).total_seconds()

            notification_types = [
                (6 * 24 * 3600, "6_days"),
                (4 * 24 * 3600, "4_days"),
                (24 * 3600, "1_day"),
                (1 * 3600, "1_hour"),
                (-1 * 3600, "1_hour_after")
            ]

            for time_delta, notification_type in notification_types:
                last_notification = db.get_last_notification(user_id, course_id, notification_type)
                if (time_delta - 60 < time_diff < time_delta + 60) and (
                        not last_notification or (now - last_notification).days >= 7):
                    if notification_type == "6_days":
                        await send_notification(user_id, f"Напоминалка: Через 6 дней пройдет наша следующая встреча.")
                        db.update_notification_log(user_id, course_id, notification_type, now)
                    elif notification_type == "4_days":
                        await send_notification(user_id, f"Напоминалка: Встреча пройдет через 4 дня.")
                        db.update_notification_log(user_id, course_id, notification_type, now)
                    elif notification_type == "1_day":
                        await send_notification(user_id,
                                                f"Напоминалка: Встреча будет уже завтра. Не забудь повторить материал, который мы прислали после прошлой встречи.")
                        db.update_notification_log(user_id, course_id, notification_type, now)
                    elif notification_type == "1_hour":
                        await send_notification(user_id,
                                                f"Напоминалка: В {appointment['time']} у тебя пройдет встреча.")
                        db.update_notification_log(user_id, course_id, notification_type, now)
                    elif notification_type == "1_hour_after":
                        await send_notification(user_id,
                                                f"Встреча подходит к концу {appointment['time']}. До встречи на следующей неделе.")
                        db.update_notification_log(user_id, course_id, notification_type, now)
                        db.update_week_number(course_id, user_id)
                        await send_skills_notification(user_id, course_id)
                        db.update_notification_log(user_id, course_id, notification_type, now)


async def send_skills_notification(user_id, course_id):
    if not db.has_sent_skills_notification(user_id, course_id):

        current_week = db.get_current_week(course_id, user_id)
        skills = db.get_skills_for_week(course_id, current_week)

        if skills:
            skills_message = "Информация для изучения на этой неделе:\n" + "\n".join(
                [f"{skill['skill']}: {skill['link']}" for skill in skills])
            await send_notification(user_id, skills_message)
            db.record_skills_notification(user_id, course_id)


# endregion

class Form(StatesGroup):
    nickname = State()


class AddCourse(StatesGroup):
    waiting_for_google_sheet_url = State()
    waiting_for_course_password = State()
    waiting_for_registration_deadline = State()


class EnrollCourse(StatesGroup):
    waiting_for_course_selection = State()
    waiting_for_course_password = State()


class SubmitHomework(StatesGroup):
    waiting_for_course_selection = State()
    waiting_for_homework_link = State()


class ViewHomework(StatesGroup):
    waiting_for_course_selection = State()
    waiting_for_course_id = State()


class SendAnnouncement(StatesGroup):
    waiting_for_announcement_details = State()


class SetAppointment(StatesGroup):
    waiting_for_user_selection = State()
    waiting_for_weekday = State()
    waiting_for_time = State()


class SetRules(StatesGroup):
    waiting_for_user_selection = State()
    waiting_for_rules_value = State()


# region Registration
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    if not db.user_exists(message.from_user.id):
        db.add_user(message.from_user.id)
        await bot.send_message(message.from_user.id, "Привет! Введи свой никнейм.")
        await Form.nickname.set()
    else:
        rules = db.get_rules(message.from_user.id)
        if rules == 0:
            await bot.send_message(message.from_user.id, "Привет!", reply_markup=navigation.MainMenu)
        elif rules == 1:
            await bot.send_message(message.from_user.id, "Привет, оператор!", reply_markup=navigation.TeacherMenu)
        elif rules == 2:
            await bot.send_message(message.from_user.id, "Привет, админ!", reply_markup=navigation.AdminMenu)


@dp.message_handler(state=Form.nickname)
async def set_nickname(message: types.Message, state: FSMContext):
    nickname = message.text
    if len(nickname) > 63:
        await bot.send_message(message.from_user.id, "Ник слишком длинный")
    else:
        db.set_nickname(message.from_user.id, nickname)
        db.set_signup(message.from_user.id, 'done')
        await bot.send_message(message.from_user.id, f"Установлен ник: {nickname}", reply_markup=navigation.Resizer)
        await state.finish()


# endregion

@dp.message_handler(commands=['Menu'])
async def menu(message: types.Message):
    rules = db.get_rules(message.from_user.id)
    if rules == 0:
        await bot.send_message(message.from_user.id, "Панель юзера!", reply_markup=navigation.MainMenu)
    elif rules == 1:
        await bot.send_message(message.from_user.id, "Панель оператора!", reply_markup=navigation.TeacherMenu)
    elif rules == 2:
        await bot.send_message(message.from_user.id, "панель админа!", reply_markup=navigation.AdminMenu)


@dp.message_handler(commands=['getrules'])
async def get_rules_command(message: types.Message):
    rules = db.get_rules(message.from_user.id)
    await bot.send_message(message.from_user.id, f"Your rules value is: {rules}")


# region SetRules
@dp.message_handler(commands=['setrules'])
async def set_rules_command(message: types.Message):
    user_rules = db.get_rules(message.from_user.id)
    if user_rules == 2:
        users = db.get_users()
        if not users:
            await message.answer("Нет доступных пользователей.")
            return

        keyboard = InlineKeyboardMarkup(row_width=1)
        for user in users[:10]:
            keyboard.add(InlineKeyboardButton(user['nickname'], callback_data=f"setrules_user_{user['user_id']}"))

        await message.answer("Выберите пользователя для изменения правил:", reply_markup=keyboard)
        await SetRules.waiting_for_user_selection.set()
    else:
        await message.answer("У вас нет прав для изменения правил пользователей.")


@dp.callback_query_handler(lambda c: c.data.startswith('setrules_user_'), state=SetRules.waiting_for_user_selection)
async def user_selected(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = int(callback_query.data.split('_')[2])
    await state.update_data(user_id=user_id)

    keyboard = InlineKeyboardMarkup(row_width=3)
    for rules_value in [0, 1, 2]:
        keyboard.add(InlineKeyboardButton(str(rules_value), callback_data=f"setrules_value_{rules_value}"))

    await bot.send_message(callback_query.from_user.id, "Выберите новое значение правил для пользователя:",
                           reply_markup=keyboard)
    await SetRules.waiting_for_rules_value.set()
    await callback_query.answer()


@dp.callback_query_handler(lambda c: c.data.startswith('setrules_value_'), state=SetRules.waiting_for_rules_value)
async def rules_value_selected(callback_query: types.CallbackQuery, state: FSMContext):
    rules_value = int(callback_query.data.split('_')[2])
    data = await state.get_data()
    user_id = data.get('user_id')

    db.set_rules(user_id, rules_value)
    await bot.send_message(callback_query.from_user.id,
                           f"Значение правил для пользователя {user_id} успешно обновлено до {rules_value}.")
    await state.finish()
    await callback_query.answer()


# endregion

# region AddCourse
@dp.message_handler(commands=['addcourse'])
async def add_course_command(message: types.Message):
    user_rules = db.get_rules(message.from_user.id)
    if user_rules >= 1:
        await bot.send_message(message.from_user.id, "Введи Google Sheets URL.")
        await AddCourse.waiting_for_google_sheet_url.set()
    else:
        await bot.send_message(message.from_user.id, "У тебя нет прав для выполнения этой функции")


@dp.message_handler(state=AddCourse.waiting_for_google_sheet_url)
async def add_google_sheet_url(message: types.Message, state: FSMContext):
    google_sheet_url = message.text
    await state.update_data(google_sheet_url=google_sheet_url)

    # Parse the Google Sheet and add skills data
    skills_data = parse_google_sheet(google_sheet_url, CREDENTIALS_FILE)
    if not skills_data:
        await bot.send_message(message.from_user.id,
                               "Failed to parse the Google Sheets. Please check the URL and try again.")
        await state.finish()
        return

    await state.update_data(skills_data=skills_data)
    await bot.send_message(message.from_user.id, "Курсы с Google Sheets загружены! Введи пароли для каждого из них.")
    await state.update_data(current_course_index=0)
    await request_next_course_details(message, state)


async def request_next_course_details(message: types.Message, state: FSMContext):
    data = await state.get_data()
    skills_data = data['skills_data']
    current_course_index = data['current_course_index']

    if current_course_index < len(skills_data):
        course_name = list(skills_data.keys())[current_course_index]
        await bot.send_message(message.from_user.id, f"Пожалуйста, введи пароль для курса: {course_name}")
        await AddCourse.waiting_for_course_password.set()
    else:
        await bot.send_message(message.from_user.id, "Все курсы были успешно добавлены!")
        await state.finish()


@dp.message_handler(state=AddCourse.waiting_for_course_password)
async def add_course_password(message: types.Message, state: FSMContext):
    data = await state.get_data()
    current_course_index = data['current_course_index']
    skills_data = data['skills_data']

    course_name = list(skills_data.keys())[current_course_index]
    password = message.text
    await state.update_data(password=password)

    await bot.send_message(message.from_user.id,
                           f"Пожалуйста, введи дату окончания регистрации: {course_name} (format YYYY-MM-DD)")
    await AddCourse.waiting_for_registration_deadline.set()


@dp.message_handler(state=AddCourse.waiting_for_registration_deadline)
async def add_registration_deadline(message: types.Message, state: FSMContext):
    registration_deadline = message.text
    try:
        datetime.strptime(registration_deadline, '%Y-%m-%d')
    except ValueError:
        await bot.send_message(message.from_user.id, "Неверный формат даты. Нужно так: YYYY-MM-DD")
        return

    data = await state.get_data()
    current_course_index = data['current_course_index']
    google_sheet_url = data['google_sheet_url']
    skills_data = data['skills_data']
    password = data['password']

    course_name = list(skills_data.keys())[current_course_index]
    db.add_course(course_name, message.from_user.id, password, registration_deadline, google_sheet_url)
    db.add_skills(course_name, skills_data[course_name])

    await state.update_data(current_course_index=current_course_index + 1)
    await request_next_course_details(message, state)
    google_sheet_url = message.text

    data = await state.get_data()
    course_name = data.get('course_name')
    password = data.get('password')
    registration_deadline = data.get('registration_deadline')

    db.add_course(course_name, message.from_user.id, password, registration_deadline, google_sheet_url)

    skills_data = parse_google_sheet(google_sheet_url, CREDENTIALS_FILE)
    for sheet_name, skills in skills_data.items():
        db.add_skills(sheet_name, skills)

    await bot.send_message(message.from_user.id, "Все добавлено! Ура!")
    await state.finish()


# endregion

# region courses
@dp.message_handler(commands=['courses'])
async def list_courses(message: types.Message):
    courses = db.get_courses()
    if courses:
        response = "Доступные курсы:\n"
        for course in courses:
            response += f"{course[0]}. {course[1]} (Регистрация заканчивается: {course[2]})\n"
        await bot.send_message(message.from_user.id, response)
    else:
        await bot.send_message(message.from_user.id, "На данный момент нет свободных курсов для регистрации.")


def get_open_courses():
    open_courses = []
    courses = db.get_courses()
    current_date = datetime.now().date()
    for course in courses:
        registration_deadline = datetime.strptime(course[2], '%Y-%m-%d').date()
        if current_date <= registration_deadline:
            open_courses.append(course)
    return open_courses


def generate_course_keyboard(courses, page=0):
    keyboard = InlineKeyboardMarkup(row_width=2)
    begin = page * 10
    end = begin + 10
    for course in courses[begin:end]:
        keyboard.add(InlineKeyboardButton(course[1], callback_data=f'enroll_course_{course[0]}'))
    if len(courses) > end:
        keyboard.add(InlineKeyboardButton("Дальше", callback_data=f'course_page_{page + 1}'))
    if page > 0:
        keyboard.add(InlineKeyboardButton("Назад", callback_data=f'course_page_{page - 1}'))
    return keyboard


# endregion

# region Enroll
@dp.message_handler(commands=['enroll'])
async def enroll_command(message: types.Message):
    open_courses = get_open_courses()
    if open_courses:
        keyboard = generate_course_keyboard(open_courses)
        await bot.send_message(message.from_user.id, "Выбери курс для записи:", reply_markup=keyboard)
        await EnrollCourse.waiting_for_course_selection.set()
    else:
        await bot.send_message(message.from_user.id, "Нет курсов для записи.")


# Показ курсов
@dp.callback_query_handler(lambda c: c.data and c.data.startswith('course_page_'),
                           state=EnrollCourse.waiting_for_course_selection)
async def paginate_courses(callback_query: CallbackQuery, state: FSMContext):
    page = int(callback_query.data.split('_')[-1])
    open_courses = get_open_courses()
    keyboard = generate_course_keyboard(open_courses, page)
    await bot.edit_message_reply_markup(callback_query.from_user.id, callback_query.message.message_id,
                                        reply_markup=keyboard)


# Запись на курс
@dp.callback_query_handler(lambda c: c.data and c.data.startswith('enroll_course_'),
                           state=EnrollCourse.waiting_for_course_selection)
async def select_course(callback_query: CallbackQuery, state: FSMContext):
    course_id = int(callback_query.data.split('_')[-1])
    await state.update_data(course_id=course_id)
    await bot.send_message(callback_query.from_user.id, "Введи пароль.")
    await EnrollCourse.waiting_for_course_password.set()


# Проверка пароля
@dp.message_handler(state=EnrollCourse.waiting_for_course_password)
async def enroll_course(message: types.Message, state: FSMContext):
    password = message.text
    data = await state.get_data()
    course_id = data['course_id']
    course_password = db.get_course_password(course_id)

    if course_password == password:
        db.enroll_user(message.from_user.id, course_id)
        await bot.send_message(message.from_user.id, "Поздравляем! Ты записан на курс")
        await state.finish()
    else:
        await bot.send_message(message.from_user.id, "Неправильный пароль. попробуй еще.")
        await EnrollCourse.waiting_for_course_password.set()


# endregion

# region Appointment
@dp.message_handler(commands=['set_appointment'])
async def set_appointment_command(message: types.Message):
    user_rules = db.get_rules(message.from_user.id)
    if user_rules >= 1:
        users = db.get_users_without_appointments()
        if not users:
            await message.reply("Нет пользователей без назначенных встреч.")
            return

        await show_user_selection(message.from_user.id, users, 0)
        await SetAppointment.waiting_for_user_selection.set()
    else:
        await message.reply("У тебя нет прав для выполнения этой функции.")


# Показ списка пользователей с инлайн-кнопками
async def show_user_selection(user_id, users, start_index):
    markup = types.InlineKeyboardMarkup(row_width=2)
    for user in users[start_index:start_index + 10]:
        markup.insert(types.InlineKeyboardButton(user[1], callback_data=f"user_{user[0]}"))

    if start_index + 10 < len(users):
        markup.add(types.InlineKeyboardButton("Вперед", callback_data=f"next_{start_index + 10}"))

    if start_index > 0:
        markup.add(types.InlineKeyboardButton("Назад", callback_data=f"prev_{start_index - 10}"))

    await bot.send_message(user_id, "Выбери пользователя:", reply_markup=markup)


# Обработка выбора пользователя
@dp.callback_query_handler(lambda c: c.data and c.data.startswith('user_'),
                           state=SetAppointment.waiting_for_user_selection)
async def process_user_selection(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = int(callback_query.data.split('_')[1])
    await state.update_data(selected_user=user_id)
    await bot.send_message(callback_query.from_user.id, "Введи день недели (например, Понедельник).")
    await SetAppointment.waiting_for_weekday.set()


# Обработка кнопок "Next" и "Previous"
@dp.callback_query_handler(lambda c: c.data and (c.data.startswith('next_') or c.data.startswith('prev_')),
                           state=SetAppointment.waiting_for_user_selection)
async def process_pagination(callback_query: types.CallbackQuery, state: FSMContext):
    start_index = int(callback_query.data.split('_')[1])
    users = db.get_users_without_appointments()
    await show_user_selection(callback_query.from_user.id, users, start_index)


# Обработка ввода дня недели
@dp.message_handler(state=SetAppointment.waiting_for_weekday)
async def process_weekday(message: types.Message, state: FSMContext):
    weekday = message.text
    await state.update_data(weekday=weekday)
    await bot.send_message(message.from_user.id, "Введи время встречи (например, 15:00).")
    await SetAppointment.waiting_for_time.set()


# Обработка ввода времени
@dp.message_handler(state=SetAppointment.waiting_for_time)
async def process_time(message: types.Message, state: FSMContext):
    time = message.text
    data = await state.get_data()
    teacher_id = message.from_user.id
    user_id = data['selected_user']
    weekday = data['weekday']

    db.add_appointment(teacher_id, user_id, weekday, time)
    await bot.send_message(message.from_user.id, "Напоминания для встречи установлены!")
    await state.finish()


# endregion

# region Homework
@dp.message_handler(commands=['submit_homework'])
async def submit_homework_command(message: types.Message):
    user_id = message.from_user.id
    courses = db.get_user_courses(user_id)

    if not courses:
        await message.answer("Вы не зарегистрированы ни на один курс.")
        return

    keyboard = InlineKeyboardMarkup(row_width=1)
    for course in courses[:10]:  # Показать до 10 курсов
        keyboard.add(InlineKeyboardButton(course['course_name'], callback_data=f"select_course_{course['id']}"))

    await message.answer("Выберите курс для отправки домашней работы:", reply_markup=keyboard)
    await SubmitHomework.waiting_for_course_selection.set()


@dp.callback_query_handler(lambda c: c.data.startswith('select_course_'),
                           state=SubmitHomework.waiting_for_course_selection)
async def course_selected(callback_query: types.CallbackQuery, state: FSMContext):
    course_id = int(callback_query.data.split('_')[2])
    await state.update_data(course_id=course_id)
    await bot.send_message(callback_query.from_user.id, "Отправьте ссылку на домашнюю работу.")
    await SubmitHomework.waiting_for_homework_link.set()
    await callback_query.answer()


@dp.message_handler(state=SubmitHomework.waiting_for_homework_link)
async def handle_homework_link(message: types.Message, state: FSMContext):
    data = await state.get_data()
    course_id = data['course_id']
    file_link = message.text

    db.submit_homework(message.from_user.id, course_id, file_link)
    await message.answer("Ссылка на домашнюю работу успешно отправлена!")
    await state.finish()


# Command to view homework submissions
@dp.message_handler(commands=['view_homework'])
async def view_homework_command(message: types.Message):
    user_rules = db.get_rules(message.from_user.id)

    if user_rules >= 1:
        if user_rules == 1:
            courses = db.get_user_courses_as_owner(message.from_user.id)
        else:
            courses = db.get_all_courses()

        if not courses:
            await message.answer("Нет доступных курсов.")
            return

        keyboard = InlineKeyboardMarkup(row_width=1)
        for course in courses[:10]:
            keyboard.add(InlineKeyboardButton(course['course_name'], callback_data=f"view_course_{course['id']}"))

        await message.answer("Выберите курс для просмотра домашних заданий:", reply_markup=keyboard)
        await ViewHomework.waiting_for_course_selection.set()
    else:
        await message.answer("У вас нет прав для просмотра домашних заданий.")


@dp.callback_query_handler(lambda c: c.data.startswith('view_course_'), state=ViewHomework.waiting_for_course_selection)
async def course_selected(callback_query: types.CallbackQuery, state: FSMContext):
    course_id = int(callback_query.data.split('_')[2])
    await state.update_data(course_id=course_id)

    homework = db.get_last_homework(course_id)
    if homework:
        response = "Последние 50 домашних заданий:\n"
        for hw in homework:
            user_nickname = db.get_nickname(hw[0])
            response += f"{user_nickname} - {hw[1]}\n"
        await bot.send_message(callback_query.from_user.id, response)
    else:
        await bot.send_message(callback_query.from_user.id, "Для этого курса нет домашних заданий.")

    await state.finish()
    await callback_query.answer()


# endregion


# region Announcement
@dp.message_handler(commands=['send_announcement'])
async def send_announcement_command(message: types.Message):
    user_rules = db.get_rules(message.from_user.id)
    if user_rules >= 1:
        await bot.send_message(message.from_user.id, "Введи ID Курса и сообщение, которое хочешь отправить.")
        await SendAnnouncement.waiting_for_announcement_details.set()
    else:
        await bot.send_message(message.from_user.id, "У тебя нет прав для выполнения этой функции.")


@dp.message_handler(state=SendAnnouncement.waiting_for_announcement_details)
async def send_announcement_details(message: types.Message, state: FSMContext):
    details = message.text.split(' ', 1)
    if len(details) != 2:
        await bot.send_message(message.from_user.id, "Не тот формат. Надо: course_id текст")
        return

    course_id, announcement = int(details[0]), details[1]
    enrolled_users = db.get_enrolled_users(course_id)

    for user in enrolled_users:
        await bot.send_message(user[0], f"Сообщение для курса {course_id}: {announcement}")

    await bot.send_message(message.from_user.id, "Уведомление отправленно!")
    await state.finish()


# endregion


if __name__ == '__main__':
    schedule_notifications()
    executor.start_polling(dp, skip_updates=True)
