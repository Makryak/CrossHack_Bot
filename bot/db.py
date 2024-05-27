import sqlite3
from datetime import datetime

class Database:
    def __init__(self, db_file):
        self.connection = sqlite3.connect(db_file)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()
        self.create_tables()

    def create_tables(self):
        with self.connection:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS `users` (
                    `id` INTEGER PRIMARY KEY AUTOINCREMENT,
                    `user_id` INTEGER UNIQUE NOT NULL,
                    `nickname` TEXT,
                    `time_sub` INTEGER NOT NULL DEFAULT 0,
                    `sign_up` TEXT DEFAULT 'setnickname',
                    `rules` INTEGER NOT NULL DEFAULT 0
                );
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS `courses` (
                    `id` INTEGER PRIMARY KEY AUTOINCREMENT,
                    `course_name` TEXT,
                    `owner_id` INTEGER NOT NULL,
                    `password` TEXT NOT NULL,
                    `registration_deadline` TEXT NOT NULL,
                    `google_sheet_url` TEXT,
                    `parsing_time` TEXT,
                    FOREIGN KEY (`owner_id`) REFERENCES `users` (`user_id`)
                );
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS `skills` (
                    `id` INTEGER PRIMARY KEY AUTOINCREMENT,
                    `course_name` TEXT NOT NULL,
                    `course_id` INTEGER NOT NULL,
                    `skill` TEXT NOT NULL,
                    `link` TEXT,
                    `start_date` TEXT NOT NULL,
                    `end_date` TEXT NOT NULL,
                    FOREIGN KEY (`course_name`) REFERENCES `courses` (`course_name`),
                    FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`)
                );
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS `enrollments` (
                    `id` INTEGER PRIMARY KEY AUTOINCREMENT,
                    `user_id` INTEGER NOT NULL,
                    `course_id` INTEGER NOT NULL,
                    `week_number` INTEGER DEFAULT 0,
                    FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`),
                    FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`)
                );
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS `homework` (
                    `id` INTEGER PRIMARY KEY AUTOINCREMENT,
                    `user_id` INTEGER NOT NULL,
                    `course_id` INTEGER NOT NULL,
                    `file_link` TEXT NOT NULL,
                    `submitted_at` TEXT NOT NULL,
                    FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`),
                    FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`)
                );
            """)
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS `appointments` (
                `id` INTEGER PRIMARY KEY AUTOINCREMENT,
                `teacher_id` INTEGER NOT NULL,
                `user_id` INTEGER NOT NULL,
                `course_id` INTEGER NOT NULL,
                `weekday` TEXT NOT NULL,
                `time` TEXT NOT NULL,
                FOREIGN KEY (`teacher_id`) REFERENCES `users` (`user_id`),
                FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`),
                FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`)
            );
        """)
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS notification_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                notification_type TEXT NOT NULL,
                last_sent DATETIME NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (course_id) REFERENCES courses (id),
                UNIQUE (user_id, course_id, notification_type)
            );
        """)
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS `skills_notifications` (
                `id` INTEGER PRIMARY KEY AUTOINCREMENT,
                `user_id` INTEGER NOT NULL,
                `course_id` INTEGER NOT NULL,
               `sent_at` TEXT NOT NULL,
                UNIQUE (`user_id`, `course_id`, `sent_at`)
            );
        """)
            self.connection.commit()

    # User methods
    def add_user(self, user_id):
        with self.connection:
            self.cursor.execute("INSERT INTO `users` (`user_id`) VALUES (?)", (user_id,))
            self.connection.commit()

    def user_exists(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT 1 FROM `users` WHERE `user_id` = ?", (user_id,)).fetchone()
            return bool(result)

    def set_nickname(self, user_id, nickname):
        with self.connection:
            self.cursor.execute("UPDATE `users` SET `nickname` = ? WHERE `user_id` = ?", (nickname, user_id))
            self.connection.commit()

    def get_signup(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT `sign_up` FROM `users` WHERE `user_id` = ?", (user_id,)).fetchone()
            if result:
                return str(result[0])
            return None

    def set_signup(self, user_id, sign_up):
        with self.connection:
            self.cursor.execute("UPDATE `users` SET `sign_up` = ? WHERE `user_id` = ?", (sign_up, user_id))
            self.connection.commit()

    def get_rules(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT `rules` FROM `users` WHERE `user_id` = ?", (user_id,)).fetchone()
            if result:
                return result[0]
            return None

    def set_rules(self, user_id, rules):
        with self.connection:
            self.cursor.execute("UPDATE `users` SET `rules` = ? WHERE `user_id` = ?", (rules, user_id))
            self.connection.commit()

    # Course methods
    '''def add_course(self, course_name, owner_id, password, registration_deadline, google_sheet_url):
        with self.connection:
            self.cursor.execute("""
                INSERT INTO `courses` (`course_name`, `owner_id`, `password`, `registration_deadline`, `google_sheet_url`, `parsing_time`)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (course_name, owner_id, password, registration_deadline, google_sheet_url, datetime.now().isoformat()))
            self.connection.commit()'''

    def add_course(self, course_name, owner_id, password, registration_deadline, google_sheet_url):
        with self.connection:
            self.cursor.execute("""
                INSERT INTO `courses` (`course_name`, `owner_id`, `password`, `registration_deadline`, `google_sheet_url`, `parsing_time`)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (course_name, owner_id, password, registration_deadline, google_sheet_url, datetime.now().isoformat()))
            self.connection.commit()
            return self.cursor.lastrowid
        
    '''def add_skills(self, course_name, skills):
        with self.connection:
            for skill in skills:
                self.cursor.execute("""
                    INSERT INTO `skills` (`course_name`, `skill`, `link`, `start_date`, `end_date`)
                    VALUES (?, ?, ?, ?, ?)
                """, (course_name, skill[0], skill[1], skill[2], skill[3]))
            self.connection.commit()'''
    
    def add_skills(self, course_id, course_name, skills):
        with self.connection:
            for skill in skills:
                self.cursor.execute("""
                    INSERT INTO `skills` (`course_name`, `course_id`, `skill`, `link`, `start_date`, `end_date`)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (course_name, course_id, skill[0], skill[1], skill[2], skill[3]))
            self.connection.commit()

    def get_courses(self):
        self.cursor.execute("SELECT id, course_name, registration_deadline FROM courses")
        return self.cursor.fetchall()

    def get_course_password(self, course_id):
        self.cursor.execute("SELECT password FROM courses WHERE id = ?", (course_id,))
        return self.cursor.fetchone()[0]

    def enroll_user(self, user_id, course_id):
        with self.connection:
            self.cursor.execute("""
                INSERT INTO enrollments (user_id, course_id, week_number)
                VALUES (?, ?, 0)
            """, (user_id, course_id))
            self.connection.commit()

    def get_user_enrollments(self, user_id):
        with self.connection:
            return self.cursor.execute("""
                SELECT e.course_id, c.course_name, e.week_number
                FROM enrollments e
                JOIN courses c ON e.course_id = c.id
                WHERE e.user_id = ?
            """, (user_id,)).fetchall()

    '''def get_skills_for_week(self, course_name, week_number):
        with self.connection:
            return self.cursor.execute("""
                SELECT skill, link FROM skills
                WHERE course_name = ? AND ? BETWEEN start_date AND end_date
            """, (course_name, week_number)).fetchall()'''

    def get_users_without_appointments(self):
        with self.connection:
            return self.cursor.execute("""
                SELECT `user_id`, `nickname` FROM `users`
                WHERE `user_id` NOT IN (SELECT `user_id` FROM `appointments`)
            """).fetchall()

    def add_appointment(self, teacher_id, user_id, weekday, time):
        with self.connection:
            self.cursor.execute("""
                INSERT INTO `appointments` (`teacher_id`, `user_id`, `weekday`, `time`)
                VALUES (?, ?, ?, ?)
            """, (teacher_id, user_id, weekday, time))
            self.connection.commit()

    def get_appointments(self):
        with self.connection:
            return self.cursor.execute("""
                SELECT `a`.`id`, `u`.`nickname`, `a`.`weekday`, `a`.`time`
                FROM `appointments` a
                JOIN `users` u ON `a`.`user_id` = `u`.`user_id`
            """).fetchall()

    def submit_homework(self, user_id, course_id, file_link):
        self.cursor.execute("""INSERT OR REPLACE INTO homework (user_id, course_id, file_link, submission_time)
                               VALUES (?, ?, ?, ?)""", (user_id, course_id, file_link, datetime.now()))
        self.connection.commit()

    def get_homework(self, course_id):
        self.cursor.execute("SELECT user_id, file_id, submission_time FROM homework WHERE course_id = ?", (course_id,))
        return self.cursor.fetchall()

    def get_students_in_course(self, course_id):
        self.cursor.execute("SELECT user_id FROM enrollments WHERE course_id = ?", (course_id,))
        return [row[0] for row in self.cursor.fetchall()]

    def get_course_schedule(self, course_id):
        with self.connection:
            result = self.cursor.execute("SELECT `id`, `lesson_time` FROM `schedules` WHERE `course_id` = ?", (course_id,)).fetchall()
            return result

    def add_schedule(self, course_id, lesson_time):
        with self.connection:
            self.cursor.execute("INSERT INTO `schedules` (`course_id`, `lesson_time`) VALUES (?, ?)", (course_id, lesson_time))
            self.connection.commit()

    def get_enrolled_users(self, course_id):
        return self.cursor.execute("SELECT `user_id` FROM `enrollments` WHERE `course_id` = ?", (course_id,)).fetchall()

    def submit_homework(self, user_id, course_id, file_link):
        with self.connection:
            self.cursor.execute("""
                INSERT INTO `homework` (`user_id`, `course_id`, `file_link`, `submitted_at`)
                VALUES (?, ?, ?, ?)
            """, (user_id, course_id, file_link, datetime.now().isoformat()))
            self.connection.commit()

    def get_homework(self, course_id):
        return self.cursor.execute("""
            SELECT `user_id`, `file_id`, `submitted_at`
            FROM `homework`
            WHERE `course_id` = ?
        """, (course_id,)).fetchall()

    def delete_enrollment(self, user_id, course_id):
        with self.connection:
            self.cursor.execute("DELETE FROM `enrollments` WHERE `user_id` = ? AND `course_id` = ?", (user_id, course_id))
            self.connection.commit()

    def get_user_enrollments(self, user_id):
        with self.connection:
            rows = self.cursor.execute("""
                SELECT e.course_id, c.course_name, e.week_number
                FROM enrollments e
                JOIN courses c ON e.course_id = c.id
                WHERE e.user_id = ?
            """, (user_id,)).fetchall()
            return [{'course_id': row[0], 'course_name': row[1], 'week_number': row[2]} for row in rows]

    def get_user_appointments(self, user_id):
        with self.connection:
            rows = self.cursor.execute("SELECT * FROM appointments WHERE user_id = ?", (user_id,)).fetchall()
            return [dict(row) for row in rows]

    def get_all_users(self):
        with self.connection:
            rows = self.cursor.execute("SELECT DISTINCT user_id FROM enrollments").fetchall()
            return [dict(row) for row in rows]

    def update_week_number(self, course_id, user_id):
        with self.connection:
            self.cursor.execute("""
                UPDATE enrollments
                SET week_number = week_number + 1
                WHERE course_id = ? AND user_id = ?
            """, (course_id, user_id))

    def get_skills_for_week(self, course_id, current_week):
        with self.connection:
            return self.cursor.execute("""
                SELECT s.skill, s.link 
                FROM skills s
                JOIN enrollments e ON s.course_id = e.course_id
                WHERE e.course_id = ? AND e.week_number = ?
            """, (course_id, current_week)).fetchall()
        
    '''def get_skills_for_week(self, course_id, user_id, current_week):
        with self.connection:
            return self.cursor.execute("""
                SELECT s.skill, s.link 
                FROM skills s
                JOIN enrollments e ON s.course_id = e.course_id
                WHERE e.course_id = ? AND e.user_id = ? AND e.week_number = ?
            """, (course_id, user_id, current_week)).fetchall()'''
    
    def has_sent_skills_notification(self, user_id, course_id):
        with self.connection:
            result = self.cursor.execute("""
                SELECT 1 FROM skills_notifications
                WHERE user_id = ? AND course_id = ?
            """, (user_id, course_id)).fetchone()
            return bool(result)
        
    def get_last_notification(self, user_id, course_id, notification_type):
        with self.connection:
            row = self.cursor.execute("""
                SELECT last_sent FROM notification_log
                WHERE user_id = ? AND course_id = ? AND notification_type = ?
            """, (user_id, course_id, notification_type)).fetchone()
            return datetime.fromisoformat(row['last_sent']) if row else None

    def update_notification_log(self, user_id, course_id, notification_type, last_sent):
        with self.connection:
            self.cursor.execute("""
                INSERT INTO notification_log (user_id, course_id, notification_type, last_sent)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (user_id, course_id, notification_type)
                DO UPDATE SET last_sent = excluded.last_sent
            """, (user_id, course_id, notification_type, last_sent))
            self.connection.commit()

    def get_current_week(self, course_id, user_id):
        with self.connection:
            result = self.cursor.execute("""
                SELECT week_number FROM enrollments
                WHERE user_id = ? AND course_id = ?
            """, (user_id, course_id)).fetchone()
            return result['week_number'] if result else None
        
    def record_skills_notification(self, user_id, course_id):
        with self.connection:
            self.cursor.execute("""
                INSERT INTO skills_notifications (user_id, course_id, sent_at)
                VALUES (?, ?, ?)
            """, (user_id, course_id, datetime.now().isoformat()))
            self.connection.commit()

    def get_user_courses_as_owner(self, user_id):
        with self.connection:
            return self.cursor.execute("""
                SELECT id, course_name
                FROM courses
                WHERE owner_id = ?
            """, (user_id,)).fetchall()

    def get_all_courses(self):
        with self.connection:
            return self.cursor.execute("SELECT id, course_name FROM courses").fetchall()

    def get_last_homework(self, course_id, limit=50):
        with self.connection:
            return self.cursor.execute("""
                SELECT user_id, file_link, submitted_at
                FROM homework
                WHERE course_id = ?
                ORDER BY submitted_at DESC
                LIMIT ?
            """, (course_id, limit)).fetchall()

    def get_nickname(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT nickname FROM users WHERE user_id = ?", (user_id,)).fetchone()
            return result['nickname'] if result else None
        
    def get_user_courses(self, user_id):
        with self.connection:
            return self.cursor.execute("""
                SELECT c.id, c.course_name
                FROM enrollments e
                JOIN courses c ON e.course_id = c.id
                WHERE e.user_id = ?
            """, (user_id,)).fetchall()
        
    def get_users(self):
        with self.connection:
            return self.cursor.execute("SELECT user_id, nickname FROM users").fetchall()

