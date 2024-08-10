import os
import json
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, session
from flask_caching import Cache
import requests
from dotenv import load_dotenv

load_dotenv()

config = {
    "DEBUG": True,  # some Flask specific configs
    "CACHE_TYPE": "SimpleCache",  # Flask-Caching related configs
    "CACHE_DEFAULT_TIMEOUT": 300,
}
app = Flask(__name__)
app.config.from_mapping(config)
app.secret_key = os.getenv("SECRET_KEY")
cache = Cache(app)


@app.get("/toggle_theme")
def toggle_theme():
    current_theme = session.get("theme")
    if current_theme == "dark":
        session["theme"] = "light"
    else:
        session["theme"] = "dark"

    return redirect(request.args.get("current_page", "readme"))


@app.get("/command")
def command():
    command = request.args.get("command")

    context = {"command": command}

    if command == "stats":
        context["stats"] = get_stats()
        return render_template("commands/stats.html", **context)
    elif command == "whoami":
        return render_template("commands/whoami.html", **context)
    elif command == "help":
        return render_template("commands/help.html", **context)
    elif command == "about":
        return render_template("commands/about.html", **context)
    else:
        return render_template("commands/invalid.html", **context)


def get_stats() -> dict:
    res = cache.get("stats")
    if res:
        return res

    res = {
        "github": {
            "followers": "N/A",  # N/A: Not Available
            "stars": "N/A",
            "repos": "N/A",
        },
        "telegram": {
            "subscribers": "N/A",
        },
        "typeracer": {
            "races": "N/A",
            "wpm": "N/A",
        },
        "chess": {"games": "N/A", "rating": "N/A"},
    }

    github_url = "https://api.github.com/users/Hereugo"
    github_repos_url = "https://api.github.com/users/Hereugo/repos?per_page=100"
    telegram_url = (
        "https://api.telegram.org/bot{}/getChatMembersCount?chat_id={}".format(
            os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHANNEL_ID")
        )
    )
    typeracer_url = "https://data.typeracer.com/users?id=tr:hereugo"
    chess_url = "https://api.chess.com/pub/player/h_reugo/stats"
    github_res = requests.get(github_url)
    github_repos_res = requests.get(github_repos_url)
    telegram_res = requests.get(telegram_url)
    typeracer_res = requests.get(typeracer_url)

    # https://www.chess.com/clubs/forum/view/403-error-2
    chess_res = requests.get(
        chess_url,
        headers={"User-Agent": "username: h_reugo, email: thereug6@gmail.com"},
    )

    if github_res.status_code == 200:
        github_data = github_res.json()
        res["github"]["followers"] = github_data["followers"]
    else:
        app.logger.error(github_res.text)

    if github_repos_res.status_code == 200:
        github_repos_data = github_repos_res.json()
        my_repos = [repo for repo in github_repos_data if not repo["fork"]]

        res["github"]["repos"] = str(len(my_repos))
        res["github"]["stars"] = str(sum(repo["stargazers_count"] for repo in my_repos))
    else:
        app.logger.error(github_repos_res.text)

    if telegram_res.status_code == 200:
        telegram_data = telegram_res.json()
        res["telegram"]["subscribers"] = telegram_data["result"]
    else:
        app.logger.error(telegram_res.text)

    if typeracer_res.status_code == 200:
        typeracer_data = typeracer_res.json()
        res["typeracer"]["races"] = typeracer_data["tstats"]["cg"]
        res["typeracer"]["wpm"] = (
            str(int(typeracer_data["tstats"]["recentAvgWpm"])) + " WPM"
        )
    else:
        app.logger.error(typeracer_res.text)

    if chess_res.status_code == 200:
        chess_data = chess_res.json()
        res["chess"]["rating"] = chess_data["chess_rapid"]["last"]["rating"]
        res["chess"]["games"] = str(sum(chess_data["chess_rapid"]["record"].values()))
    else:
        app.logger.error(chess_res)

    cache.set("stats", res)

    return res


@app.route("/")
@app.route("/readme")
def readme():
    context = {
        "title": "readme",
    }

    return render_template("readme.html", **context)


@app.route("/projects")
def projects():
    projects = cache.get("projects")

    if not projects:
        with open("projects.json") as f:
            projects = json.load(f)

        projects = sorted(
            projects,
            key=lambda x: datetime.strptime(x["start_date"], "%b %d, %Y"),
            reverse=True,
        )

        cache.set("projects", projects)

    context = {
        "title": "projects",
        "projects": projects,
    }
    return render_template("projects.html", **context)


@app.errorhandler(404)
def not_found(error):
    return redirect(url_for("readme"))
