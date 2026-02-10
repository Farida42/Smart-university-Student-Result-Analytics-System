CREATE DATABASE IF NOT EXISTS smart_result;
USE smart_result;

-- ---------------- USERS ----------------
CREATE TABLE users (
  user_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(120) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role ENUM('admin','teacher','student') NOT NULL
);

CREATE TABLE students (
  student_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  dept VARCHAR(80),
  batch VARCHAR(20),
  section VARCHAR(10),
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE teachers (
  teacher_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  dept VARCHAR(80),
  designation VARCHAR(80),
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- ---------------- ACADEMIC ----------------
CREATE TABLE courses (
  course_id INT AUTO_INCREMENT PRIMARY KEY,
  code VARCHAR(20) UNIQUE NOT NULL,
  title VARCHAR(150) NOT NULL,
  credit DECIMAL(3,1) NOT NULL DEFAULT 3.0
);

CREATE TABLE semesters (
  semester_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(40) NOT NULL,
  year INT NOT NULL
);

CREATE TABLE enrollments (
  enroll_id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  course_id INT NOT NULL,
  semester_id INT NOT NULL,
  FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
  FOREIGN KEY (course_id) REFERENCES courses(course_id) ON DELETE CASCADE,
  FOREIGN KEY (semester_id) REFERENCES semesters(semester_id) ON DELETE CASCADE
);

ALTER TABLE enrollments
ADD UNIQUE KEY uniq_enroll(student_id, course_id, semester_id);

CREATE TABLE course_teachers (
  ct_id INT AUTO_INCREMENT PRIMARY KEY,
  teacher_id INT NOT NULL,
  course_id INT NOT NULL,
  semester_id INT NOT NULL,
  section VARCHAR(10) DEFAULT NULL,
  UNIQUE(teacher_id, course_id, semester_id, section),
  FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id) ON DELETE CASCADE,
  FOREIGN KEY (course_id) REFERENCES courses(course_id) ON DELETE CASCADE,
  FOREIGN KEY (semester_id) REFERENCES semesters(semester_id) ON DELETE CASCADE
);

-- ---------------- MARKS ----------------
CREATE TABLE mark_components (
  comp_id INT AUTO_INCREMENT PRIMARY KEY,
  course_id INT NOT NULL,
  name VARCHAR(60) NOT NULL,
  max_marks DECIMAL(6,2) NOT NULL,
  weight DECIMAL(6,2) NOT NULL,
  FOREIGN KEY (course_id) REFERENCES courses(course_id) ON DELETE CASCADE
);

CREATE TABLE marks (
  mark_id INT AUTO_INCREMENT PRIMARY KEY,
  enroll_id INT NOT NULL,
  comp_id INT NOT NULL,
  obtained_marks DECIMAL(6,2) NOT NULL,
  UNIQUE(enroll_id, comp_id),
  FOREIGN KEY (enroll_id) REFERENCES enrollments(enroll_id) ON DELETE CASCADE,
  FOREIGN KEY (comp_id) REFERENCES mark_components(comp_id) ON DELETE CASCADE
);

-- ---------------- ATTENDANCE ----------------
CREATE TABLE attendance (
  att_id INT AUTO_INCREMENT PRIMARY KEY,
  enroll_id INT UNIQUE NOT NULL,
  total_class INT NOT NULL DEFAULT 0,
  attended_class INT NOT NULL DEFAULT 0,
  FOREIGN KEY (enroll_id) REFERENCES enrollments(enroll_id) ON DELETE CASCADE
);

-- ---------------- RESULTS ----------------
CREATE TABLE results (
  result_id INT AUTO_INCREMENT PRIMARY KEY,
  enroll_id INT UNIQUE NOT NULL,
  total_percent DECIMAL(5,2) NOT NULL,
  letter_grade VARCHAR(3) NOT NULL,
  grade_point DECIMAL(3,2) NOT NULL,
  is_published TINYINT(1) NOT NULL DEFAULT 0,
  published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (enroll_id) REFERENCES enrollments(enroll_id) ON DELETE CASCADE
);

CREATE TABLE student_semester_gpa (
  ssg_id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  semester_id INT NOT NULL,
  gpa DECIMAL(3,2) NOT NULL,
  total_credits DECIMAL(5,2) NOT NULL,
  UNIQUE(student_id, semester_id),
  FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
  FOREIGN KEY (semester_id) REFERENCES semesters(semester_id) ON DELETE CASCADE
);

-- ---------------- SEED (optional) ----------------
-- Semesters
INSERT INTO semesters(name, year) VALUES
('Spring', 2025), ('Summer', 2025), ('Fall', 2025);

-- Courses
INSERT INTO courses(code, title, credit) VALUES
('CSE-101', 'Introduction to Programming', 3.0),
('CSE-102', 'Data Structures', 3.0),
('CSE-201', 'Database Systems', 3.0);

-- Components
INSERT INTO mark_components(course_id, name, max_marks, weight)
SELECT course_id, 'Quiz', 20, 20 FROM courses WHERE code='CSE-101';
INSERT INTO mark_components(course_id, name, max_marks, weight)
SELECT course_id, 'Mid', 30, 30 FROM courses WHERE code='CSE-101';
INSERT INTO mark_components(course_id, name, max_marks, weight)
SELECT course_id, 'Final', 50, 50 FROM courses WHERE code='CSE-101';

INSERT INTO mark_components(course_id, name, max_marks, weight)
SELECT course_id, 'Quiz', 20, 20 FROM courses WHERE code='CSE-102';
INSERT INTO mark_components(course_id, name, max_marks, weight)
SELECT course_id, 'Mid', 30, 30 FROM courses WHERE code='CSE-102';
INSERT INTO mark_components(course_id, name, max_marks, weight)
SELECT course_id, 'Final', 50, 50 FROM courses WHERE code='CSE-102';

INSERT INTO mark_components(course_id, name, max_marks, weight)
SELECT course_id, 'Quiz', 20, 20 FROM courses WHERE code='CSE-201';
INSERT INTO mark_components(course_id, name, max_marks, weight)
SELECT course_id, 'Mid', 30, 30 FROM courses WHERE code='CSE-201';
INSERT INTO mark_components(course_id, name, max_marks, weight)
SELECT course_id, 'Final', 50, 50 FROM courses WHERE code='CSE-201';

-- Demo users: replace HASH_* after running make_hash.py
INSERT INTO users(name, email, password_hash, role) VALUES
('Admin User', 'admin@demo.com', 'HASH_ADMIN', 'admin'),
('Teacher One', 'teacher@demo.com', 'HASH_TEACHER', 'teacher'),
('Student One', 'student@demo.com', 'HASH_STUDENT', 'student');

INSERT INTO teachers(user_id, dept, designation)
SELECT user_id, 'CSE', 'Lecturer' FROM users WHERE email='teacher@demo.com';

INSERT INTO students(user_id, dept, batch, section)
SELECT user_id, 'CSE', '2021', 'A' FROM users WHERE email='student@demo.com';

-- Enroll student in Spring 2025
INSERT INTO enrollments(student_id, course_id, semester_id)
SELECT s.student_id, c.course_id, sem.semester_id
FROM students s, courses c, semesters sem
WHERE s.section='A' AND sem.name='Spring' AND sem.year=2025
AND c.code IN ('CSE-101','CSE-102','CSE-201')
ON DUPLICATE KEY UPDATE student_id=student_id;

-- Init attendance rows
INSERT INTO attendance(enroll_id, total_class, attended_class)
SELECT e.enroll_id, 0, 0 FROM enrollments e
ON DUPLICATE KEY UPDATE enroll_id=enroll_id;
