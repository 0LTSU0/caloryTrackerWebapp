import sqlite3
import hashlib
import threading
import time

PWD_SALT = "thisissomestringtobeusedasasaltforpwdhashing"
TOKEN_SALT = "thisissomestringtobeusedassaltfortokens"
LOGIN_VALIDITY_TIME = 60 * 60 * 24 * 7 #token expires one week from now
UNKNOWN_USER_ID = -1
DEFAULT_CALORY_TARGET = 2000
DEFAULT_WEIGHT_GOAL = 0

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
        print("init_database(), loading userdata to memory")
        user_rows = self.cur.execute('SELECT * FROM users').fetchall()
        for row in user_rows:
            #row is: id, username, pwdhash, sessiontoken, sessiontokenexp, dailycalories, weightgoal, normaldailyburn
            username = row[1]
            self.registered_users[username] = {"pwdhash": row[2], "sessiontoken": row[3], "sessiontokenexp": row[4], "id": row[0], "dailycalorylimit": row[5], "weightgoal": row[6], "defaultdailyburn": row[7], "food_records": [], "weight_records": [], "exercise_records": []}
            for f_row in self.cur.execute(f'SELECT * FROM userdata_foods_{username} ORDER BY datetime ASC').fetchall():
                #row is: id, datetime, food, calories, note
                entry = {"datetime": f_row[1], "food": f_row[2], "note": f_row[3]}
                self.registered_users[username]["food_records"].append(entry)
                print("Loaded entry", entry, "for user", username)
            for w_row in self.cur.execute(f'SELECT * FROM userdata_weights_{username} ORDER BY datetime ASC').fetchall():
                #row is: id, datetime, weight
                entry = {"datetime": w_row[1], "weight": w_row[2]}
                self.registered_users[username]["weight_records"].append(entry)
                print("Loaded entry", entry, "for user", username)
            for e_row in self.cur.execute(f'SELECT * FROM userdata_exercises_{username} ORDER BY datetime ASC').fetchall():
                #row is: id, datetime, exercise, calories, desc
                entry = {"datetime": e_row[1], "exercise": e_row[2], "calories": e_row[3], "desc": e_row[4]}
                self.registered_users[username]["exercise_records"].append(entry)
                print("Loaded entry", entry, "for user", username)


    #init general tables like users and in case someone is missing user data, create those tables also
    def init_tables(self):
        res = self.cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        if not ("users",) in res:
            print("Users table does not exist in db, creating now")
            self.cur.execute("CREATE TABLE users(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, pwdhash TEXT, sessiontoken TEXT, sessiontokenexp INTEGER, dailycalories INTEGER, weightgoal REAL, normaldailyburn INTEGER)")
        else:
            print("users table already in db, creating userdata tables for anyone missing one")
            for row in self.cur.execute('SELECT * FROM users').fetchall():
                user_table_name = f"userdata_foods_{row[1]}"
                if not (user_table_name,) in res:
                    self.init_user_data_table(user_table_name)
                user_table_name = f"userdata_weights_{row[1]}"
                if not (user_table_name,) in res:
                    self.init_user_data_table(user_table_name)
                user_table_name = f"userdata_exercises_{row[1]}"
                if not (user_table_name,) in res:
                    self.init_user_data_table(user_table_name)
                    
    #NOTE: only call this inside with thlock or in init steps
    def init_user_data_table(self, table_name):
        if "foods" in table_name:
            print("Creating table:", table_name)
            self.cur.execute(f"CREATE TABLE {table_name}(id INTEGER PRIMARY KEY AUTOINCREMENT, datetime INTEGER, food TEXT, calories REAL, note TEXT)")
        elif "weights" in table_name:
            print("Creating table:", table_name)
            self.cur.execute(f"CREATE TABLE {table_name}(id INTEGER PRIMARY KEY AUTOINCREMENT, datetime INTEGER, weight REAL)")
        elif "exercises" in table_name:
            print("Creating table:", table_name)
            self.cur.execute(f"CREATE TABLE {table_name}(id INTEGER PRIMARY KEY AUTOINCREMENT, datetime INTEGER, calories REAL, desc TEXT)")
        else:
            print("Attempted to create unknown type of userdata table", table_name)

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
                self.init_user_data_table(f"userdata_foods_{username}")
                self.init_user_data_table(f"userdata_weights_{username}")
                self.init_user_data_table(f"userdata_exercises_{username}")
            self.registered_users[username] = {"pwdhash": pwd_hash, "sessiontoken": token, "sessiontokenexp": expiry, "id": UNKNOWN_USER_ID, "dailycalorylimit": DEFAULT_CALORY_TARGET, "weightgoal": DEFAULT_WEIGHT_GOAL, "defaultdailyburn": DEFAULT_CALORY_TARGET, "food_records": [], "weight_records": [], "exercise_records": []} #TODO: if user id is used for something it needs to be set to correct value
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