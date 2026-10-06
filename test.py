#connection test database, loaded the .env file and get the DATABASE_URL in app/config.py
import psycopg2

def test_database_connection():
    try:
        # Load the database URL from the .env file
        from app.config import Config
        database_url = Config.SQLALCHEMY_DATABASE_URI

        # Establish a connection to the PostgreSQL database
        connection = psycopg2.connect(database_url)
        cursor = connection.cursor()

        # Execute a simple query to test the connection
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()
        print(f"Database connection successful. PostgreSQL version: {db_version[0]}")

    except Exception as e:
        print(f"Error connecting to the database: {e}")

    finally:
        # Close the cursor and connection,
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'connection' in locals() and connection:
            connection.close()

if __name__ == "__main__":
    test_database_connection()