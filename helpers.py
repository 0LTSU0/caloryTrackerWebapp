import re
import time
from datetime import datetime as dt

def is_integer(s): #from chatgpt :)
    return re.fullmatch(r"[+-]?\d+", s) is not None

def is_float(s): #from chatgpt :)
    return re.fullmatch(r"[+-]?\d*\.\d+", s) is not None

def epoch_to_ddmmyyyy(epoch_time):
    return time.strftime('%d%m%Y', time.gmtime(epoch_time))

def ddmmyyy_to_datetime(timestring):
    return dt.strptime(timestring, "%d%m%Y")

def get_what_needs_update_day(old_data, new_data):
    pass
    #if some old record is no longer in new_data, it must be requested to be deleted
    # Also 
    delete_items, add_items = [], []
    for old_d in old_data:
        shall_be_deleted = True
        for new_d in new_data:
            if new_d == old_d: #if some new d is old then no delete
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
        item["datetime"] = int(item["datetime"])
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

