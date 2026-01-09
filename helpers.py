import re
import time
import os
import json
import sys
import base64
import requests
from datetime import datetime as dt
from datetime import timedelta as td
from datetime import timezone

class exerciseRecord():
    def __init__(self, timestamp, calories, desc, gpx_path="", extra_data_avaibale=False, pf_id=None):
        #ntry = {"datetime": e_row[1], "calories": e_row[2], "desc": e_row[3], "gpx_path": extra_data_path, "extra_data_available": extra_data_available}
        self.datetime = timestamp
        self.calories = calories
        self.desc = desc
        self.gpx_path = gpx_path
        self.extra_data_available = extra_data_avaibale
        self.pf_id = pf_id #this is only used when syncing with polar flow

    def __eq__(self, other):
        return self.datetime == other.datetime and self.calories == other.calories and self.desc == other.desc
    
class activityRecord():
    def __init__(self, id, starttime, endttime, activeduration, inactiveduration, dailyactivity, calories, activecalories, steps, inactivityalerts, distancefromsteps):
        self.id = id
        self.starttime = starttime
        self.endttime = endttime
        self.activeduration = activeduration
        self.inactiveduration = inactiveduration
        self.dailyactivity = dailyactivity
        self.calories = calories
        self.activecalories = activecalories
        self.steps = steps
        self.inactivityalerts = inactivityalerts
        self.distancefromsteps = distancefromsteps
        self.source = "Polar Flow" # currently only possibility for getting these

    @classmethod
    def fromdbrow(cls, row):
        return cls(
            row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10]
        )
    
    @classmethod
    def fromjsonentry(cls, entry):
        if entry["start_time"].count(":") == 2:
            start_ts = dt.strptime(entry["start_time"], "%Y-%m-%dT%H:%M:%S").timestamp()
        else:
            start_ts = dt.strptime(entry["start_time"], "%Y-%m-%dT%H:%M").timestamp()
        if entry["end_time"].count(":") == 2:
            end_ts = dt.strptime(entry["end_time"], "%Y-%m-%dT%H:%M:%S").timestamp()
        else:
            end_ts = dt.strptime(entry["end_time"], "%Y-%m-%dT%H:%M").timestamp()
        return cls(
            None, #dont know primarykey id here but we dont really need it for anything anyway so whatever
            start_ts,
            end_ts,
            ISO8601_duration_to_seconds(entry["active_duration"]),
            ISO8601_duration_to_seconds(entry["inactive_duration"]),
            float(entry["daily_activity"]),
            int(entry["calories"]),
            int(entry["active_calories"]),
            int(entry["steps"]),
            int(entry["inactivity_alert_count"]),
            float(entry["distance_from_steps"])
        )
    
    def __str__(self):
        s = "activityRecord Object: "
        for key, value in vars(self).items():
            s += f"{key}: {value}, "
        return s
    
    def __eq__(self, other):
        for key, value in vars(self).items():
            if key == "id":
                continue # ids dont matter for comparison
            if vars(other).get(key) != value:
                return False
        return True


def is_integer(s): #from chatgpt :)
    return re.fullmatch(r"[+-]?\d+", s) is not None

def is_float(s): #from chatgpt :)
    return re.fullmatch(r"[+-]?\d*\.\d+", s) is not None

def epoch_to_ddmmyyyy(epoch_time):
    return time.strftime('%d%m%Y', time.localtime(epoch_time))

def ddmmyyy_to_datetime(timestring):
    return dt.strptime(timestring, "%d%m%Y")

def compare_e_items(_1, _2):
    return _1["datetime"] == _2["datetime"] and _1["calories"] == _2["calories"] and _1["desc"] == _2["desc"]

def ISO8601_duration_to_seconds(duration: str) -> int:
    match = re.fullmatch(
        r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?",
        duration
    )
    if not match:
        raise ValueError(f"Invalid duration: {duration}")

    hours, minutes, seconds = match.groups(default="0")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds)

def e_data_json_to_obj(ds):
    res = []
    for d in ds:
        res.append(exerciseRecord(d["datetime"], d["calories"], d["desc"]))
    return res

def get_what_needs_update_day(old_data, new_data):
    pass
    #if some old record is no longer in new_data, it must be requested to be deleted
    # Also 
    delete_items, add_items = [], []
    for old_d in old_data:
        shall_be_deleted = True
        for new_d in new_data:
            
            if old_d == new_d: #if some new d is old then no delete
                shall_be_deleted = False
                break
        if shall_be_deleted:
            delete_items.append(old_d)

    for new_d in new_data:
        shall_be_added = True
        for old_d in old_data:
            if old_d == new_d: #if some old d is new then no add
                shall_be_added = False
                break
        if shall_be_added:
            add_items.append(new_d)
    return delete_items, add_items
    
def numerize_food_vals_in_new_data(data):
    converted = []
    for item in data:
        try:
            item["calories"] = float(item["calories"])
        except ValueError:
            item["calories"] = 0.0
        item["datetime"] = int(float(item["datetime"]))
        converted.append(item)
    return converted

def generate_autofill_recommendations(f_entries):
    tmp = {}
    for entry in f_entries:
        tupl = create_recommendation_tuple(entry)
        if not tupl:
            continue
        if tupl in tmp.keys():
            tmp[tupl] += 1
        else:
            tmp[tupl] = 1
    #at this point well have dict with item: number of occurances -> sort and return the tuples
    sorted_foods = [key for key, value in sorted(tmp.items(), key=lambda item: item[1], reverse=True)]
    return sorted_foods

def create_recommendation_tuple(f_entry):
    if f_entry.get("food") and f_entry.get("calories"): #only create tuple if food name and calories exist
        t = (f_entry.get("food"), f_entry.get("calories"))
        return t
    return None

def epoch_for_date(date, eod=False):
    #date is string in format of DDMMYYY and mode is eod (end of day -> epoch for that day at 23:59:59) or sod (start of day -> epoch for that day at 0:0:0)
    curr_date = ddmmyyy_to_datetime(date) # this results in timestamp at sod
    if eod:
        curr_date = curr_date.replace(hour=23, minute=59, second=59)
    return curr_date.timestamp()

def get_datestring_at_offset(date, offset):
    #date is some DDMMYYY string. If offset is e.g. -7, this function returns DDMMYYY from a week ago
    start_date = ddmmyyy_to_datetime(date)
    new_date = start_date + td(days=offset)
    return epoch_to_ddmmyyyy(new_date.timestamp())

def get_pf_integration_info():
    # get polar flow client id from environment or file
    client_id = os.environ.get("pf_client_id")
    client_secret = os.environ.get("pf_client_secret")
    if client_id and client_secret:
        return client_id, client_secret
    try:
        with open("pfoauth.json", "r") as f:
            pfouathjson = json.load(f)
            return pfouathjson["client_id"], pfouathjson["client_secret"] 
    except:
        print("Failed to get polar flow client id from env and file -> exiting")
        sys.exit(1)

def get_pf_access_token(code, id, secret):
    # fetch polar flow access token using authentication key (https://www.polar.com/accesslink-api/?srsltid=AfmBOopLXX7JJ7BclEFUp2NQwykxiEgvIaiK0T-R-QiRO6nARfKAVZIo#token-endpoint)
    auth = base64.urlsafe_b64encode(f"{id}:{secret}".encode("utf-8")).decode("utf-8").rstrip("=")
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'Authorization': f"Basic {auth}"
    }
    body = {
        "grant_type": "authorization_code",
        "code": code
    }
    r = requests.post('https://polarremote.com/v2/oauth2/token', data=body, headers=headers)
    if r.status_code != 200:
        return None, None
    r_json = r.json()
    print("Polar Flow token request returned:", r_json)
    return r_json["access_token"], int(time.time() + int(r.json()["expires_in"])), int(r_json.get("x_user_id"))


def register_pf_user(username, access_token):
    # register user with accesslink https://www.polar.com/accesslink-api/?python#register-user
    body = {
        "member-id": f"pf_{username}"
    }
    headers = {
        'Content-Type': 'application/json',  'Accept': 'application/json',  'Authorization': f'Bearer {access_token}'
    }
    r = requests.post('https://www.polaraccesslink.com/v3/users', headers = headers, json=body)
    if r.status_code >= 200 and r.status_code < 400:
        print("User registration with polar access link ok:", r.json())
    elif r.status_code == 409:
        print("User already registered with polar access link")
    else:
        print("User registration with polar access link failed")


def fetch_new_trainingdata_from_pf(userdata):
    # Note to self: Polar flow only gives you exercise data that you have not fetched yet when using exercise-transactions. This means we don't need to worry about adding same entry multiple times
    if not userdata.get("pf_integration").is_connected():
        return None
    pf_token = userdata.get("pf_integration").token
    pf_uid = userdata.get("pf_integration").pf_user_id

    #create transaction
    h = {'Accept': 'application/json',  'Authorization': f'Bearer {pf_token}'}
    r = requests.post(f'https://www.polaraccesslink.com/v3/users/{pf_uid}/exercise-transactions', headers=h)
    if r.status_code >= 400 or r.status_code == 204: # 204 = no new content avaible
        return None
    r_json = r.json()
    transaction_id = r_json["transaction-id"]

    #get list of exercises
    r = requests.get(f'https://www.polaraccesslink.com/v3/users/{pf_uid}/exercise-transactions/{transaction_id}', headers=h)
    if r.status_code >= 400:
        return None
    r_json = r.json()

    #get data of all available exercises
    ex_data = []
    h_gpx = {'Accept': 'application/gpx+xml',  'Authorization': f'Bearer {pf_token}'}
    h_fit = {'Accept': '*/*',  'Authorization': f'Bearer {pf_token}'}
    for exercise_link in r_json["exercises"]:
        data = requests.get(exercise_link, headers=h)
        d_json = data.json()
        print(f'got new exercise for user {userdata.get("id")} from polar flow:', d_json)
        start_time = dt.strptime(d_json["start-time"], "%Y-%m-%dT%H:%M:%S")
        #start_time = start_time.replace(tzinfo=timezone.utc)
        #epoch_ts = int(start_time.timestamp() + (int(d_json["start-time-utc-offset"]) * 60))
        epoch_ts = start_time.timestamp()
        ex_data.append(exerciseRecord(epoch_ts, d_json["calories"], f'PF: {d_json["detailed-sport-info"]}', pf_id=d_json["id"]))
        gpx_dir = f'pf_data_{d_json["id"]}'
        os.mkdir(gpx_dir)
        if d_json["has-route"]:
            # if route data is available, get gpx (though .fit seems to be way better format and we can do everything with it, download these for now just in case)
            r_gpx = requests.get(exercise_link + "/gpx", headers=h_gpx)
            with open(gpx_dir + "/route.gpx", "w") as f:
                f.write(r_gpx.text)
        
        #always get the fit file
        r_fit = requests.get(exercise_link + "/fit", headers=h_fit)        
        with open(gpx_dir + "/data.fit", "wb") as f:
            f.write(r_fit.content)

    #close transaction
    h = {'Authorization': f'Bearer {pf_token}'}
    r = requests.put(f'https://www.polaraccesslink.com/v3/users/{pf_uid}/exercise-transactions/{transaction_id}', headers=h)

    return ex_data


# TODO, if we sync pf multiple times during the same day, we currently end up with multiple entries with same start time but different end time and values in the db.
# So if start times are same, the existing entry should be updated instead of adding new
def get_new_activity_info_from_pf(userdata):
    if not userdata.get("pf_integration").is_connected():
        return None
    pf_token = userdata.get("pf_integration").token
    pf_uid = userdata.get("pf_integration").pf_user_id
    h = {'Accept': 'application/json',  'Authorization': f'Bearer {pf_token}'}
    r = requests.get(f'https://www.polaraccesslink.com/v3/users/activities', headers=h)
    if r.status_code == 401:
        print("https://www.polaraccesslink.com/v3/users/activities returned unauthorized")
        return
    elif r.status_code == 403:
        print("https://www.polaraccesslink.com/v3/users/activities returned forbidden")
        return
    elif r.status_code != 200:
        print(f"Unexpected status code from polaraccesslink.com/v3/users/activities {r.status_code}")
        return

    # Check if we already have this entry
    js = r.json()
    new_entries = []
    for entry in js:
        fetched_aRecord = activityRecord.fromjsonentry(entry)
        add = True
        for existing_aRecord in userdata["activity_records"]:
            if fetched_aRecord == existing_aRecord:
                add = False
                break
        if add:
            new_entries.append(fetched_aRecord)
    return new_entries
