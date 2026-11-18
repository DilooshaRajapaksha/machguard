import getpass

from app import db, security, users

db.init_db()
security.get_secret()

print("Create an administrator account for MachGuard\n")
username = input("Username (for example admin): ").strip()
full_name = input("Full name: ").strip()

while True:
    password = getpass.getpass("Password (typing is hidden): ")
    again = getpass.getpass("Type it again: ")
    if password != again:
        print("The two passwords are different. Try again.\n")
        continue
    try:
        security.check_password_rules(password, username)
    except ValueError as problem:
        print(problem, "\n")
        continue
    break

if users.get_by_username(username):
    print("That username already exists.")
else:
    users.create(username, full_name, security.hash_password(password), "admin", must_change=False)
    users.audit("setup", "admin_created", username)
    print("Done. You can now log in as", username)