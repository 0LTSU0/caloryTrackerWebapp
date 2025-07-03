import os
from flask import Flask
from flask import redirect, render_template, url_for, request, jsonify, send_from_directory, make_response

from dbaccess import *
from helpers import *
from plotgen import *

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
db_access = None

# PolarFlow integration
PF_AUTH_URL = "https://flow.polar.com/oauth2/authorization"
PF_CLIENT_ID = None
PF_CLIENT_SECRET = None

@app.route("/")
def main():
    ses_token = request.cookies.get("session")
    if ses_token:
        if db_access.check_session_token_validity(ses_token):
            return redirect(url_for("foods_wo_date"))
    return redirect(url_for("login"))


@app.route("/foods/day/<date>", methods=["GET"])
def foods_day(date):
    ses_token = request.cookies.get("session")
    if not ses_token:
        return redirect("/login")
    if not db_access.check_session_token_validity(ses_token):
        return redirect("/login")
    username = ses_token.split("|")[0]
    if request.method == "GET":
        daily_foods = db_access.get_entries_day(username, date, "food_records")
        daily_exercises = db_access.get_entries_day(username, date, "exercise_records")
        dailylimit, defaultburn, weightgoal = db_access.fill_settings_form(username)
        sum_eaten = round(sum([float(x['calories']) for x in daily_foods]), 2)
        sum_exercised = round(sum([float(x['calories']) for x in daily_exercises]), 2)
        if (sum_eaten - sum_exercised) < dailylimit:
            text = f"You have eaten {sum_eaten}kcal and exercised {sum_exercised}kcal today. For your {dailylimit}kcal target, you have {round(dailylimit+sum_exercised-sum_eaten, 2)}kcal remaining."
            text_good = True
        else:
            text = f"You have eaten {sum_eaten}kcal and exercised {sum_exercised}kcal today. For your {dailylimit}kcal target, you are {round(abs(dailylimit-sum_eaten+sum_exercised), 2)}kcal over."
            text_good = False
        recommendations = generate_autofill_recommendations(db_access.get_entries_all(username, "food_records"))

        
        #todo move plot stuff to separate method
        plot_endt = epoch_for_date(date, True)
        plot_startt = epoch_for_date(get_datestring_at_offset(date, -7), False)
        plot_data = db_access.get_daily_entries_in_range(username, plot_startt, plot_endt)
        plotly, avg = generate_food_record_plot(plot_data, dailylimit)

        return render_template("foods.html",
                               username=username,
                               date=date,
                               records=daily_foods,
                               e_records=daily_exercises,
                               remainder_text=text,
                               remainder_text_positive=text_good,
                               foodrecms=recommendations,
                               plotlyhtml=plotly,
                               avg=avg)
    

@app.route("/foods/day/<date>/post", methods=["POST"])
def add_new_foods_day(date): #NOTE: this also handles exercises since they are on the same page
    ses_token = request.cookies.get("session")
    if not ses_token:
        return redirect("/login")
    if not db_access.check_session_token_validity(ses_token):
        return redirect("/login")
    username = ses_token.split("|")[0]
    redirect_addr = request.base_url.rstrip("/post")
    fdata = request.get_json()["foods"]
    fdata = numerize_food_vals_in_new_data(fdata)
    edata = request.get_json()["exercises"]
    edata = numerize_food_vals_in_new_data(edata)
    current_fitems_on_day = db_access.get_entries_day(username, date, "food_records")
    current_eitems_on_day = db_access.get_entries_day(username, date, "exercise_records")
    fitems_to_delete, fitems_to_add = get_what_needs_update_day(current_fitems_on_day, fdata)
    eitems_to_delete, eitems_to_add = get_what_needs_update_day(current_eitems_on_day, edata)
    db_access.add_foods_for_user(username, fitems_to_add)
    db_access.delete_foods_for_user(username, fitems_to_delete)
    db_access.add_exercises_for_user(username, eitems_to_add)
    db_access.delete_exercises_for_user(username, eitems_to_delete)
    return redirect(redirect_addr)


@app.route("/foods/day")
def foods_wo_date():
    date = epoch_to_ddmmyyyy(time.time()) #when accessing without requested date, assume server's today
    return redirect(url_for("foods_day", date=date))


@app.route("/profile/<user>", methods=['GET', 'POST'])
def profile_page(user):
    ses_token = request.cookies.get("session")
    if not ses_token:
        return redirect("/login")
    if not db_access.check_session_token_validity(ses_token):
        return redirect("/login")
    if not ses_token.split("|")[0] == user:
        return "You can't access other people's profile settings. Go away >:("
    if request.method == "GET":
        daily_target, daily_burn, weight_goal, pf_connected = db_access.fill_settings_form(user)
        return render_template("profile.html",
                               username=user,
                               daily_target=daily_target,
                               daily_burn=daily_burn,
                               weight_goal=weight_goal,
                               show_error_msg=False,
                               error_msg="",
                               pf_connected=pf_connected)
    elif request.method == "POST":
        error_msg = ""
        new_daily_target = request.form.get("daily_calory_target_input")
        new_daily_burn = request.form.get("daily_calory_burn_input")
        new_weight_goal = request.form.get("weight_goal_input")
        if not new_daily_target or not is_integer(new_daily_target):
            error_msg += "Daily target needs to be integer! "
        if not new_daily_burn or not is_integer(new_daily_burn):
            error_msg += "Daily burn needs to be integer! "
        if not new_weight_goal or not is_float(new_weight_goal):
            error_msg += "Weight goal needs to be float! "
        show_error_msg = error_msg != ""
        if not show_error_msg:
            succ, error = db_access.update_profile_settings(user, new_daily_target, new_daily_burn, new_weight_goal)
            if not succ:
                show_error_msg = True
                error_msg += error
        return render_template("profile.html",
                               username=user,
                               daily_target=new_daily_target,
                               daily_burn=new_daily_burn,
                               weight_goal=new_weight_goal,
                               show_error_msg=show_error_msg,
                               error_msg=error_msg)
    

@app.route("/weights/<user>", methods=["GET"])
def weights_page(user):
    ses_token = request.cookies.get("session")
    if not ses_token:
        return redirect("/login")
    if not db_access.check_session_token_validity(ses_token):
        return redirect("/login")
    if not ses_token.split("|")[0] == user:
        return "You can't access other people's records. Go away >:("
    weight_records = db_access.get_weight_records_for_user(user)
    dailylimit, defaultburn, weightgoal = db_access.fill_settings_form(user)
    plot = ""
    if len(weight_records) > 0:
        plot = generate_weight_plot(weight_records, weightgoal)
    return render_template("weights.html",
                           username=user,
                           weight_records=weight_records,
                           plot=plot)


@app.route("/weights/<user>/post", methods=["POST"])
def post_new_weight(user):
    ses_token = request.cookies.get("session")
    if not ses_token:
        return redirect("/login")
    if not db_access.check_session_token_validity(ses_token):
        return redirect("/login")
    if not ses_token.split("|")[0] == user:
        return "You can't access other people's records. Go away >:("
    
    try:
        ts = int(request.get_json()["ts"])
        weight = float(request.get_json()["weight"])
        db_access.add_weight_for_user(user, ts, weight)
        print("TODO save:", ts, weight)
    except Exception as e:
        print(e) #Todo show error on page or whatever
        return redirect(redirect_addr)

    redirect_addr = request.base_url.rstrip("/post")
    return redirect(redirect_addr)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == "GET":
        return render_template("login.html")
    else:
        usrname = request.form.get('username')
        if db_access.check_login(usrname, request.form.get('password')):
            print(f"login info ok for user {usrname}, updating session token to db")
            new_token = db_access.update_session_token_for_user(usrname)
            if new_token:
                response = make_response(redirect("/"))
                response.set_cookie('session', f"{usrname}|{new_token}", max_age=LOGIN_VALIDITY_TIME)
                return response
        else:
            return render_template("login.html", show_error_msg=True)
        

@app.route("/logout", methods=['GET'])
def logout():
    ses_token = request.cookies.get("session")
    if ses_token:
        db_access.invalidate_sestoken(ses_token)
        
    return redirect("/login")

        
@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == "GET":
        return render_template("register.html")
    else:
        username, password, repassword = request.form.get("username"), request.form.get("password"), request.form.get("repassword")
        if not password == repassword or not username or not password or not repassword:
            return render_template("register.html", show_error_msg=True)
        success, token = db_access.create_new_account(username, password)
        if not success:
            return render_template("register.html", show_error_msg=True)
        response = make_response(redirect("/"))
        response.set_cookie('session', f"{username}|{token}", max_age=LOGIN_VALIDITY_TIME)
        return response

@app.route("/check_username_taken/<name>")
def check_username_taken(name):
    return jsonify(db_access.check_if_user_exists(name))

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route("/pfoauth")
def pfoauth():
    code = request.args.get('code')
    ses_token = request.cookies.get("session")
    if not code or not ses_token or not db_access.check_session_token_validity(ses_token):
        return "PolarFlow authorization failed"
    username = ses_token.split("|")[0]
    access_token, token_expiry = get_pf_access_token(code, PF_CLIENT_ID, PF_CLIENT_SECRET)
    if not access_token or not token_expiry:
        return "PolarFlow authorization failed"
    db_access.update_pf_code_for_user(username, code, access_token, token_expiry)
    return redirect(f"/profile/{username}")
    

@app.route("/connectPolarFlow")
def connectPolarFlow():
    auth_url = f"{PF_AUTH_URL}?response_type=code&client_id={PF_CLIENT_ID}"
    return redirect(auth_url)


if __name__ == "__main__":
    PF_CLIENT_ID, PF_CLIENT_SECRET = get_pf_integration_info()
    db_access = dbAccess()
    db_access.init_database()
    app.run(host="0.0.0.0", port=5000, debug=False)
    