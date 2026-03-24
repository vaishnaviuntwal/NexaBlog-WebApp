from werkzeug.security import generate_password_hash, check_password_hash
hash_pw = generate_password_hash("hello123", method="pbkdf2:sha256")
print(hash_pw)
print(check_password_hash(hash_pw, "hello123"))
