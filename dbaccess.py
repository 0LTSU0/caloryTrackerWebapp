import sqlite3
import hashlib
import threading
import time

PWD_SALT = "thisissomestringtobeusedasasaltforpwdhashing"
TOKEN_SALT = "thisissomestringtobeusedassaltfortokens"
LOGIN_VALIDITY_TIME = 60 * 60 * 24 * 7 #token expires one week from now
UNKNOWN_USER_ID = -1

def hash_password(pwd):
    hash = pwd + PWD_SALT 
    hash = hashlib.md5(hash.encode()).hexdigest()
    print(f"password {pwd} created hash {hash}")
    return hash

def generate_login_token(username):
    hash = username + TOKEN_SALT + str(time.time())
    hash = hashlib.md5(hash.encode()).hexdigest()
    exp = int(time.time()) + LOGIN_VALIDITY_TIME
    return hash, exp

class dbAccess():
    def __init__(self):
        self.db = None
        self.cur = None
        self.thlock = threading.Lock() #with many users this would be stupid bottleneck but cant be arsed to implement separate connection for each request
        self.registered_users = {} #users in db to reduce times db needs to be queried
    
    def init_database(self): #if some table is missing from db, it is created and also current stuff contained inside db is loaded into memory
        self.db = sqlite3.connect("db.db", check_same_thread=False)
        self.cur = self.db.cursor()
        self.init_tables()
        print("init_database(), loading users to memory")
        user_rows = self.cur.execute('SELECT * FROM users').fetchall()
        for row in user_rows:
            #row is: id, username, pwdhash, sessiontoken, sessiontokenexp
            self.registered_users[row[1]] = {"pwdhash": row[2], "sessiontoken": row[3], "sessiontokenexp": row[4], "id": row[0]}

    def init_tables(self):
        res = self.cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        if not ("users",) in res:
            print("Users table does not exist in db, creating now")
            self.cur.execute("CREATE TABLE users(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, pwdhash TEXT, sessiontoken TEXT, sessiontokenexp INTEGER)")

    def check_login(self, username, pwd):
        #with self.thlock:
        if not username or not pwd:
            return False
        print("Checking if following user exists:", username)
        #user_exists = self.cur.execute(f"SELECT True FROM users WHERE username='{username}'").fetchone()
        if not username in self.registered_users.keys(): #user does not exist
            return False
        #with self.thlock:
        #    db_user = self.cur.execute(f"SELECT * FROM users WHERE username='{username}'").fetchone()
        return hash_password(pwd) == self.registered_users[username].get("pwdhash") #everything ok so far, check password

    def check_if_user_exists(self, username):
        return username in self.registered_users.keys()
    
    def create_new_account(self, username, password):
        if self.check_if_user_exists(username):
            return False
        pwd_hash = hash_password(password)
        token, expiry = generate_login_token(username)
        sql = f"INSERT INTO users (username, pwdhash, sessiontoken, sessiontokenexp) VALUES ('{username}', '{pwd_hash}', '{token}', {expiry})"
        
        try:
            with self.thlock:
                self.cur.execute(sql)
                self.db.commit()
            self.registered_users[username] = {"pwdhash": pwd_hash, "sessiontoken": token, "sessiontokenexp": expiry, "id": UNKNOWN_USER_ID} #TODO: if user id is used for something it needs to be set to correct value
            return True, token
        except Exception as e:
            print("Exception in create_new_account()", e)
            return False, ""
        
    def update_session_token_for_user(self, user):
        token, exp = generate_login_token(user)
        try:
            with self.thlock:
                sql = "UPDATE users SET sessiontoken = ?, sessiontokenexp = ? WHERE username = ?"
                self.cur.execute(sql, (token, exp, user))
                self.db.commit()
            ddata = self.registered_users[user]
            ddata["sessiontoken"] = token
            ddata["sessiontokenexp"] = exp
            self.registered_users[user] = ddata
            return token
        except Exception as e:
            print("Error in update_session_token_for_user()", e)
            return None

    def check_session_token_validity(self, ses_token):
        username = ses_token.split("|")[0]
        token = ses_token.split("|")[1]
        if not username in self.registered_users.keys() or token != self.registered_users[username].get("sessiontoken") or time.time() > self.registered_users[username].get("sessiontokenexp"):
            return False
        return True