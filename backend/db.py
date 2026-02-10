import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="1345",   # <-- change
        database="smart_result"
    )
