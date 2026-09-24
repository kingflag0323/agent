import sqlite3

def find_user(user_id: str):
    connection = sqlite3.connect(":memory:")
    # Deliberately unsafe: request input is concatenated into SQL.
    query = "SELECT id, name, email FROM users WHERE id = " + user_id
    return connection.execute(query).fetchall()
