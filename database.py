import psycopg2


def get_connection():
    connection = psycopg2.connect(
        host="localhost",
        database="shopeasy",
        user="postgres",
        password="Rajeswari@123",
        port="5433"
    )

    return connection

def create_products_table():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            price INTEGER NOT NULL,
            category VARCHAR(50) NOT NULL,
            image VARCHAR(255)
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()

if __name__ == "__main__":
    try:
        conn = get_connection()
        print("PostgreSQL connected successfully!")
        conn.close()

        create_products_table()
        print("Products table created successfully!")
    except Exception as e:
        print("Connection failed:", e)