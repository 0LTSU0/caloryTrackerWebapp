import sqlite3
import hashlib
import threading
import time
import datetime
import shutil

from helpers import *

PWD_SALT = "thisissomestringtobeusedasasaltforpwdhashing"
TOKEN_SALT = "thisissomestringtobeusedassaltfortokens"
LOGIN_VALIDITY_TIME = 60 * 60 * 24 * 7 #token expires one week from now
UNKNOWN_USER_ID = -1
DEFAULT_CALORY_TARGET = 2000
DEFAULT_WEIGHT_GOAL = 80

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


class PolarFlowConnection():
    def __init__(self):
        self.auth_code = None # TODO: check if actually needed for anything? I guess it gets invalidated when token is generated
        self.token = None
        self.token_exp = None
        self.pf_user_id = None

    def is_connected(self):
        if not self.auth_code or not self.token or not self.token_exp or not self.pf_user_id:
            return False
        return time.time() < self.token_exp





class dbAccess():
    def __init__(self):
        self.db = None
        self.cur = None
        self.thlock = threading.Lock() #with many users this would be stupid bottleneck but cant be arsed to implement separate connection for each request
        self.registered_users = {} #users in db to reduce times db needs to be queried
    
    def init_database(self): #if some table is missing from db, it is created and also current stuff contained inside db is loaded into memory
        self.db = sqlite3.connect("db.db", check_same_thread=False)
        self.cur = self.db.cursor()
        
        #self.cur.execute("DROP TABLE thirdpartyconnections")

        self.init_tables()
        print("init_database(), loading userdata to memory")
        user_rows = self.cur.execute('SELECT * FROM users').fetchall()
        for row in user_rows:
            #row is: id, username, pwdhash, sessiontoken, sessiontokenexp, dailycalories, weightgoal, normaldailyburn
            username = row[1]
            self.registered_users[username] = {"pwdhash": row[2], "sessiontoken": row[3], "sessiontokenexp": row[4], "id": row[0], "dailycalorylimit": row[5], "weightgoal": row[6], "defaultdailyburn": row[7], "food_records": [], "weight_records": [], "exercise_records": [], "activity_records": [], "pf_integration": PolarFlowConnection()}
            print("Loaded user:", username, self.registered_users[username])
            for f_row in self.cur.execute(f'SELECT * FROM userdata_foods_{username} ORDER BY datetime ASC').fetchall():
                #row is: id, datetime, food, calories, note
                entry = {"datetime": f_row[1], "food": f_row[2], "calories": f_row[3], "note": f_row[4]}
                self.registered_users[username]["food_records"].append(entry)
                print("Loaded entry", entry, "for user", username)
            self.registered_users[username]["autofills"] = generate_autofill_recommendations(self.registered_users[username]["food_records"])
            for w_row in self.cur.execute(f'SELECT * FROM userdata_weights_{username} ORDER BY datetime ASC').fetchall():
                #row is: id, datetime, weight
                entry = {"datetime": w_row[1], "weight": w_row[2]}
                self.registered_users[username]["weight_records"].append(entry)
                print("Loaded entry", entry, "for user", username)
            for e_row in self.cur.execute(f'SELECT * FROM userdata_exercises_{username} ORDER BY datetime ASC').fetchall():
                #row is: id, datetime, calories, desc
                extra_data_path = f"pf_data/{username}/{e_row[0]}"
                extra_data_available = os.path.exists(extra_data_path)
                entry = exerciseRecord(e_row[1], e_row[2], e_row[3], extra_data_path, extra_data_available)
                self.registered_users[username]["exercise_records"].append(entry)
                print("Loaded entry", entry, "for user", username)
            for a_row in self.cur.execute(f'SELECT * FROM userdata_activity_{username} ORDER BY id ASC').fetchall():
                entry = activityRecord.fromdbrow(a_row)
                self.registered_users[username]["activity_records"].append(entry)
                print(f"Loaded entry: {entry} for user {username}")
        self.load_third_party_integration_table()


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
                user_table_name = f"userdata_activity_{row[1]}"
                if not (user_table_name,) in res:
                    self.init_user_data_table(user_table_name)
        if not ("thirdpartyconnections",) in res:
            print("No thirdparty service table in db, creating it")
            self.init_thridparty_table()
                    
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
        elif "activity" in table_name:
            print("Creating table:", table_name)
            self.cur.execute(f"CREATE TABLE {table_name}(id INTEGER PRIMARY KEY AUTOINCREMENT, starttime INTEGER, endttime INTEGER, activeduration INTEGER, inactiveduration INTEGER, dailyactivity REAL, calories INTEGER, activecalories INTEGER, steps INTEGER, inactivityalerts INTEGER, distancefromsteps REAL)")
        else:
            print("Attempted to create unknown type of userdata table", table_name)

    def init_thridparty_table(self):
        self.cur.execute("CREATE TABLE thirdpartyconnections(id INTEGER, username TEXT, pf_code TEXT, pf_token TEXT, pf_token_exp INTEGER, pf_user_id INTEGER)")

    def check_login(self, username, pwd):
        #with self.thlock:
        if not username or not pwd:
            return False
        print("Checking if following user exists:", username)
        if not username in self.registered_users.keys(): #user does not exist
            return False
        return hash_password(pwd) == self.registered_users[username].get("pwdhash") #everything ok so far, check password
    
    def invalidate_sestoken(self, cookie):
        username = cookie.split("|")[0]
        if not username or not self.check_if_user_exists(username):
            return #this was called with some nonsense token
        try:
            self.registered_users[username]["sessiontoken"] = ""
            self.registered_users[username]["sessiontokenexp"] = 0
            sql = "UPDATE users SET sessiontoken = ?, sessiontokenexp = ? WHERE username = ?"
            with self.thlock:
                self.cur.execute(sql, ("token", 0, username))
                self.db.commit()
        except: #whatever, token must have been invalid to begin with if something above failed
            pass

    def check_if_user_exists(self, username):
        return username in self.registered_users.keys()
    
    def create_new_account(self, username, password):
        if self.check_if_user_exists(username):
            return False
        pwd_hash = hash_password(password)
        token, expiry = generate_login_token(username)
        sql = f"INSERT INTO users (username, pwdhash, sessiontoken, sessiontokenexp, dailycalories, weightgoal, normaldailyburn) VALUES ('{username}', '{pwd_hash}', '{token}', {expiry}, {DEFAULT_CALORY_TARGET}, {DEFAULT_WEIGHT_GOAL}, {DEFAULT_CALORY_TARGET})"
        try:
            with self.thlock:
                self.cur.execute(sql)
                self.db.commit()
                self.init_user_data_table(f"userdata_foods_{username}")
                self.init_user_data_table(f"userdata_weights_{username}")
                self.init_user_data_table(f"userdata_exercises_{username}")
            self.registered_users[username] = {"pwdhash": pwd_hash, "sessiontoken": token, "sessiontokenexp": expiry, "id": UNKNOWN_USER_ID, "dailycalorylimit": DEFAULT_CALORY_TARGET, "weightgoal": DEFAULT_WEIGHT_GOAL, "defaultdailyburn": DEFAULT_CALORY_TARGET, "food_records": [], "weight_records": [], "exercise_records": [], "pf_integration": PolarFlowConnection()} #TODO: if user id is used for something it needs to be set to correct value
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
        if not username or not token or not username in self.registered_users.keys() or token != self.registered_users[username].get("sessiontoken") or time.time() > self.registered_users[username].get("sessiontokenexp"):
            return False
        return True
    
    def fill_settings_form(self, user):
        userdata = self.registered_users.get(user)
        if not userdata:
            return 0, 0, 0, False
        return userdata.get("dailycalorylimit"), userdata.get("defaultdailyburn"), userdata.get("weightgoal"), userdata.get("pf_integration").is_connected()
    
    def update_profile_settings(self, user, daily_calory, daily_burn, weight_goal):
        try:
            daily_calory_c = int(daily_calory)
            daily_burn_c = int(daily_burn)
            weight_goal_c = float(weight_goal)
            with self.thlock:
                sql = "UPDATE users SET dailycalories = ?, normaldailyburn = ?, weightgoal = ? WHERE username = ?"
                self.cur.execute(sql, (daily_calory_c, daily_burn_c, weight_goal_c, user))
                self.db.commit()
            self.registered_users[user]["dailycalorylimit"] = daily_calory_c
            self.registered_users[user]["defaultdailyburn"] = daily_burn_c
            self.registered_users[user]["weightgoal"] = weight_goal_c
            return True, ""
        except Exception as e:
            return False, "Unexpected error: " + str(e)
        
    def get_entries_day(self, user, date, search):
        curr_date = ddmmyyy_to_datetime(date)
        start_epoch = curr_date.timestamp()
        curr_date += datetime.timedelta(days=1)
        end_epoch = curr_date.timestamp()
        res = []
        if search == "activity_records":
            last_match = None
            for arecord in self.registered_users[user][search]:
                if arecord.starttime >= start_epoch and arecord.endttime < end_epoch:
                    last_match = arecord
            return last_match
        else:
            for frecord in self.registered_users[user][search]:
                if search == "exercise_records":
                    if frecord.datetime >= start_epoch and frecord.datetime < end_epoch:
                        res.append(frecord)
                else:
                    if frecord["datetime"] >= start_epoch and frecord["datetime"] < end_epoch:
                        res.append(frecord)
            return res
    
    def get_daily_entries_in_range(self, user, st, et): #TODO: imporove this whole graph generation logic, it currently translates timestamps to strings back many times for no reason
        curr_date = dt.fromtimestamp(st)
        res = {}
        while curr_date.timestamp() < et:
            key = f"{curr_date.day}.{curr_date.month}.{curr_date.year}"
            foods = self.get_entries_day(user, epoch_to_ddmmyyyy(curr_date.timestamp()), "food_records")
            exercises = self.get_entries_day(user, epoch_to_ddmmyyyy(curr_date.timestamp()), "exercise_records")
            activity = self.get_entries_day(user, epoch_to_ddmmyyyy(curr_date.timestamp()), "activity_records")
            res[key] = {"food": foods, "exercise": exercises, "activity": activity}
            curr_date = curr_date + td(days=1)
        return res
    
    #note to self: should be used somewhat sparingly since might return a lot of stuff
    def get_entries_all(self, user, search):
        res = []
        for frecord in self.registered_users[user][search]:
            res.append(frecord)
        return res
    
    def add_foods_for_user(self, user, add_foods):
        try:
            tablename = f"userdata_foods_{user}"
            with self.thlock:
                for entry in add_foods:
                    datetime = entry["datetime"]
                    food = entry['food']
                    calories = entry['calories']
                    note = entry['note']
                    sql = f"INSERT INTO {tablename} (datetime, food, calories, note) VALUES (?, ?, ?, ?)"
                    self.registered_users[user]["food_records"].append({"datetime": datetime, "food": food, "calories": calories, "note": note})
                    self.cur.execute(sql, (datetime, food, calories, note))
                self.db.commit()
        except Exception as e:
            print(e)

    def delete_foods_for_user(self, user, delete_foods):
        try:
            tablename = f"userdata_foods_{user}"
            with self.thlock:
                for entry in delete_foods:
                    datetime = entry["datetime"]
                    food = entry['food']
                    calories = entry['calories']
                    note = entry['note']
                    sql = f'DELETE FROM {tablename} WHERE datetime = ? AND food = ? AND calories = ? AND note = ?'
                    self.registered_users[user]["food_records"].remove({"datetime": datetime, "food": food, "calories": calories, "note": note})
                    self.cur.execute(sql, (datetime, food, calories, note))
                self.db.commit()
        except Exception as e:
            print(e)

    def add_exercises_for_user(self, user, add_exercises):
        if not add_exercises:
            return
        try:
            tablename = f"userdata_exercises_{user}"
            with self.thlock:
                for entry in add_exercises:
                    datetime = entry.datetime
                    calories = entry.calories
                    desc = entry.desc
                    sql = f"INSERT INTO {tablename} (datetime, calories, desc) VALUES (?, ?, ?)"
                    self.cur.execute(sql, (datetime, calories, desc))
                    new_item_id = self.cur.lastrowid
                    extra_data_available = False
                    if entry.pf_id: #this is available when were adding exercises from polar flow sync
                        src_path = f"pf_data_{entry.pf_id}"
                        target_path = f"pf_data/{user}"
                        target_path_with_id = f"pf_data/{user}/{new_item_id}"
                        if os.path.isdir(src_path):
                            if not os.path.isdir("pf_data"):
                                os.mkdir("pf_data")
                            if not os.path.isdir(target_path):
                                os.mkdir(target_path)
                            os.mkdir(target_path_with_id)
                            try:
                                os.rename(src_path+"/route.gpx", target_path_with_id+"/route.gpx")
                            except:
                                pass # gpx only exists if excercise has route
                            os.rename(src_path+"/data.fit", target_path_with_id+"/data.fit")
                            shutil.rmtree(src_path)
                            extra_data_available = True
                    entry = exerciseRecord(datetime, calories, desc, f"pf_data/{user}/{new_item_id}", extra_data_available)
                    self.registered_users[user]["exercise_records"].append(entry)
                self.db.commit()
        except Exception as e:
            print(e)


    def add_activity_records_for_user(self, user: str, add_activities: list[activityRecord]) -> None:
        if not add_activities:
            return
        tablename = f"userdata_activity_{user}"
        try:
            with self.thlock:
                for entry in add_activities:
                    sql = f"INSERT INTO {tablename} (starttime, endttime, activeduration, inactiveduration, dailyactivity, calories, activecalories, steps, inactivityalerts, distancefromsteps) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                    self.cur.execute(sql, (entry.starttime, entry.endttime, entry.activeduration, entry.inactiveduration, entry.dailyactivity, entry.calories, entry.activecalories, entry.steps, entry.inactivityalerts, entry.distancefromsteps))
                    self.registered_users[user]["activity_records"].append(entry)
                self.db.commit()
        except Exception as e:
            print(e)


    def delete_exercises_for_user(self, user, delete_exercises):
        try:
            tablename = f"userdata_exercises_{user}"
            with self.thlock:
                for entry in delete_exercises:
                    datetime = entry.datetime
                    calories = entry.calories
                    desc = entry.desc
                    items_to_remove = []
                    for item in self.registered_users[user]["exercise_records"]:
                        if item == exerciseRecord(datetime, calories, desc, None, None):
                            items_to_remove.append(item)
                    for item in items_to_remove:
                        self.registered_users[user]["exercise_records"].remove(item)
                    sql = f'DELETE FROM {tablename} WHERE datetime = ? AND calories = ? AND desc = ?'
                    self.cur.execute(sql, (datetime, calories, desc))
                self.db.commit()
        except Exception as e:
            print(e)

    def add_weight_for_user(self, username, add_ts, add_weight):
        try:
            tablename = f"userdata_weights_{username}"
            with self.thlock:
                sql = f"INSERT INTO {tablename} (datetime, weight) VALUES (?, ?)"
                self.cur.execute(sql, (add_ts, add_weight))
                self.db.commit()
            self.registered_users[username]["weight_records"].append({"datetime": add_ts, "weight": add_weight})
        except Exception as e:
            print(e)

    def get_weight_records_for_user(self, user):
        return self.registered_users[user]["weight_records"]
    
    def update_pf_code_for_user(self, username, code, access_token, access_token_expiry, pf_id):
        user_id = self.registered_users.get(username).get("id")
        curr_user = self.registered_users.get(username)
        if curr_user.get("pf_integration").is_connected(): # if we're updating pre-existing entry
            sql = "UPDATE thirdpartyconnections SET pf_code = ?, pf_token = ?, pf_token_exp = ?, pf_user_id = ? WHERE username = ?"
            with self.thlock:
                self.cur.execute(sql, (code, access_token, access_token_expiry, pf_id, username))
                self.db.commit()
        else:
            sql = f"INSERT INTO thirdpartyconnections (id, username, pf_code, pf_token, pf_token_exp, pf_user_id) VALUES (?, ?, ?, ?, ?, ?)"
            with self.thlock:
                self.cur.execute(sql, (user_id, username, code, access_token, access_token_expiry, pf_id))
                self.db.commit()
        pf_int = self.registered_users.get(username).get("pf_integration")
        pf_int.auth_code = code
        pf_int.token = access_token
        pf_int.token_exp = access_token_expiry
        pf_int.pf_user_id = pf_id

    def load_third_party_integration_table(self):
        for username, userdata in self.registered_users.items():
            sql = 'SELECT * FROM thirdpartyconnections WHERE username = ?'
            tp_integration_data = self.cur.execute(sql, (username,)).fetchall()
            if not tp_integration_data:
                continue
            if len(tp_integration_data) > 1:
                print(f"WARNING: THIRDPARTYCONNECTION TABLE CONTAINS MORE THAN ONE ENTRY FOR USER {username}. This should not happen so defaulting to the first one")
            pf_integration = userdata.get("pf_integration")
            pf_integration.auth_code = tp_integration_data[0][2]
            pf_integration.token = tp_integration_data[0][3]
            pf_integration.token_exp = tp_integration_data[0][4]
            pf_integration.pf_user_id = tp_integration_data[0][5]
