from werkzeug.security import generate_password_hash

print("ADMIN:", generate_password_hash("admin123"))
print("TEACHER:", generate_password_hash("teacher123"))
print("STUDENT:", generate_password_hash("student123"))
