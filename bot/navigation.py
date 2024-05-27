from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

Resizer = ReplyKeyboardMarkup(resize_keyboard=True)
Button123 = KeyboardButton('/Menu')  # ГОТОВО
Resizer.add(Button123)

# Главное меню
MainMenu = ReplyKeyboardMarkup(resize_keyboard=True)
button_courses = KeyboardButton('/Courses')  # ПЕРЕДЕЛАТЬ
button_enroll = KeyboardButton('/Enroll')  # ДОДЕЛАТЬ
MainMenu.add(button_courses, button_enroll)

# Админ меню
AdminMenu = ReplyKeyboardMarkup(resize_keyboard=True)
button_add_course = KeyboardButton('/addcourse')  # 50/50 ПЕРЕДЕЛАТЬ
# button_update_course = KeyboardButton('Update Courses') # СДЕЛАТЬ
# button_modify_course_teacher = KeyboardButton('Modify My Courses') # СДЕЛАТЬ
# button_delete_user = KeyboardButton('Delete User') # ГОТОВО (ВРОДЕ)
button_view_homework = KeyboardButton('/set_appointment')  # ДОДЕЛАТЬ
button_send_notification = KeyboardButton('/send_announcement')  # ГОТОВО (ДОДЕЛАТЬ)
button_change_rules = KeyboardButton('Change User Rules(НС)')  # СДЕЛАТЬ
AdminMenu.add(button_add_course, button_view_homework, button_send_notification, button_change_rules)

# Меню преподавателя
TeacherMenu = ReplyKeyboardMarkup(resize_keyboard=True)
button_add_course_teacher = KeyboardButton('/addcourse')  # 50/50 ПЕРЕДЕЛАТЬ
button_modify_course_teacher = KeyboardButton('Modify My Courses(НС)')  # СДЕЛАТЬ
button_view_homework = KeyboardButton('View Homework(НС)')  # ДОДЕЛАТЬ
button_send_announcement = KeyboardButton('/send_announcement')  # ГОТОВО
TeacherMenu.add(button_add_course_teacher, button_modify_course_teacher, button_view_homework, button_send_announcement)
