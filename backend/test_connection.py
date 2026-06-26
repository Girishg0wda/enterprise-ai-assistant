import psycopg2

try:
    conn = psycopg2.connect(
        host="127.0.0.1",
        database="enterprise_ai",
        user="admin",
        password="admin123",
        port=5433
    )

    print("✅ Connected successfully!")

    conn.close()

except Exception as e:
    print(e)