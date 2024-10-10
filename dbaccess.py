import sqlite3
import hashlib
import threading

class dbAccess():
    def __init__(self):
        self.db = None
        self.cur = None
        self.thlock = threading.Lock() #with many users this would be stupid bottleneck but cant be arsed to implement separate connection for each request
        self.registered_users = [] #list of users in db
    
    def init_database(self):
        self.db = sqlite3.connect("db.db", check_same_thread=False)
        self.cur = self.db.cursor()
        self.init_tables()

    def init_tables(self):
        res = self.cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        if not ("users",) in res:
            print("Users table does not exist in db, creating now")
            self.cur.execute("CREATE TABLE users(id INTEGER PRIMARY KEY, username TEXT, pwdhash TEXT, sessiontoken TEXT)")

    def check_login(self, username, pwd):
        with self.thlock:
            print("Checking if following user exists:", username)
            user_exists = self.cur.execute(f"SELECT True FROM users WHERE username='{username}'").fetchone()
        if not user_exists:
            return False #TODO: make sure there are no more than one of the same user
        with self.thlock:
            db_user = self.cur.execute(f"SELECT * FROM users WHERE username='{username}'").fetchone()
        input_pwd_hash = hashlib.sha256(username.encode()).hexdigest()
        print(input_pwd_hash)

    def check_if_user_exists(self, username):
        return username in self.registered_users