import os
from flask import Flask
from flask import redirect, render_template, url_for, request, jsonify, send_from_directory, make_response

from dbaccess import *

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
db_access = None

@app.route("/")
def main():
    ses_token = request.cookies.get("session")
    if ses_token:
        if db_access.check_session_token_validity(ses_token):
            return "this will be the home for user"
    return redirect(url_for("login"))


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
        daily_target, daily_burn, weight_goal = db_access.fill_settings_form(user)
        return render_template("profile.html",
                               username=user,
                               daily_target=daily_target,
                               daily_burn=daily_burn,
                               weight_goal=weight_goal)
    elif request.method == "POST":
        return "saving TBD"


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

if __name__ == "__main__":
    db_access = dbAccess()
    db_access.init_database()
    app.run(host="0.0.0.0", port=5000, debug=False)
    