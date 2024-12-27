from flask import Flask, redirect, url_for

app = Flask(__name__)

@app.route("/")
def home_page():
    return redirect(url_for("welcome_page", name = "Olya"))

@app.route("/welcome<name>")
def welcome_page(name):
    return "<p>Welcome {}</p>".format(name)

if __name__ == "__main__":
    app.run(debug=True, port=8080)