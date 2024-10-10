import os
from flask import Flask
from flask import redirect, render_template, url_for, request, jsonify, send_from_directory

from dbaccess import *

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
db_access = None

@app.route("/")
def main():
    return redirect(url_for("login"))

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == "GET":
        return render_template("login.html")
    else:
        if db_access.check_login(request.form.get('username'), request.form.get('password')):
            print("login info ok")
        else:
            return render_template("login.html", show_error_msg=True)
        
@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == "GET":
        return render_template("register.html")
    else:
       print("TBD")

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
    app.run(port=5000, debug=False)
    