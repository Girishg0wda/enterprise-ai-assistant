from app.auth.hashing import hash_password, verify_password

password = "admin123"

hashed = hash_password(password)

print("Password:", password)
print("Hash:", hashed)

print(
    verify_password(
        "admin123",
        hashed,
    )
)