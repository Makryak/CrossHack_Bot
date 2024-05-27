from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

Resizer = ReplyKeyboardMarkup(resize_keyboard=True)
Button123 = KeyboardButton('/Menu')  # ГОТОВО
Resizer.add(Button123)

# Главное меню
MainMenu = ReplyKeyboardMarkup(resize_keyboard=True)
button_courses = KeyboardButton('/Courses')  # ПЕРЕДЕЛАТЬ
button_enroll = KeyboardButton('/Enroll')  # ДОДЕЛАТЬ
button_submit_homework = KeyboardButton('/submit_homework')
MainMenu.add(button_courses, button_enroll, button_submit_homework)

# Админ меню
AdminMenu = ReplyKeyboardMarkup(resize_keyboard=True)
button_add_course = KeyboardButton('/addcourse')  # 50/50 ПЕРЕДЕЛАТЬ
# button_update_course = KeyboardButton('Update Courses') # СДЕЛАТЬ
# button_modify_course_teacher = KeyboardButton('Modify My Courses') # СДЕЛАТЬ
button_set_rules = KeyboardButton('/setrules') # ГОТОВО (ВРОДЕ)
button_set_appointment = KeyboardButton('/set_appointment')  # ДОДЕЛАТЬ
button_view_homework = KeyboardButton('/view_homework')
button_send_notification = KeyboardButton('/send_announcement')  # ГОТОВО
AdminMenu.add(button_add_course, button_set_appointment, button_view_homework, button_set_rules, button_send_notification)

# Меню преподавателя
TeacherMenu = ReplyKeyboardMarkup(resize_keyboard=True)
button_add_course_teacher = KeyboardButton('/addcourse')  # 50/50 ПЕРЕДЕЛАТЬ
button_modify_course_teacher = KeyboardButton('Modify My Courses(НС)')  # СДЕЛАТЬ
button_view_homework = KeyboardButton('/view_homework')  # ДОДЕЛАТЬ
button_send_announcement = KeyboardButton('/send_announcement')  # ГОТОВО
TeacherMenu.add(button_add_course_teacher, button_modify_course_teacher, button_view_homework, button_send_announcement)
