from flask import Flask, redirect, url_for, render_template

app = Flask(__name__)

movies = ["Movie1", "Movie2", "Movie3"]


@app.route("/")
def home_page():
    # bu html sayfasının içine bu id ve movies adlı değişken gönderdim
    return render_template("home_page.html")


@app.route("/movies")
def movies_page():
    return render_template("movies.html")


if __name__ == "__main__":
    app.run(debug=True, port=8080)
