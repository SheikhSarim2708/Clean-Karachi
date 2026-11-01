import pymysql
from config import DB

def get_db():
    return pymysql.connect(**DB, cursorclass=pymysql.cursors.DictCursor)