from flask import Flask
from flask import redirect, render_template, url_for

app = Flask(__name__)

@app.route("/")
def main():
    return redirect(url_for("login"))

@app.route("/login")
def login():
    return render_template("login.html")

if __name__ == "__main__":
    app.run(port=5000, debug=True)