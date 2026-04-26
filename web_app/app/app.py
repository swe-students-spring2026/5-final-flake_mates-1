import os

from flask import Flask, redirect, render_template, request, session, url_for
from pymongo import MongoClient
from bson import ObjectId
from werkzeug.security import check_password_hash, generate_password_hash

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(
    __name__,
    template_folder=os.path.join(base_dir, "templates"),
    static_folder=os.path.join(base_dir, "static")
)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")


def get_users_collection():
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    mongo_dbname = os.getenv("MONGO_DBNAME", "flakemate")
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
    client.admin.command("ping")
    db = client[mongo_dbname]
    return db["users"]


@app.route("/")
def index():
    return redirect(url_for("sign_in"))


@app.route("/sign-in", methods=["GET", "POST"])
def sign_in():
    error = None

    if request.method == "POST":
        phone_number = request.form.get("phone_number", "").strip()
        password = request.form.get("password", "")

        users = get_users_collection()
        user = users.find_one({"phone_number": phone_number})

        if not user or not check_password_hash(user["password_hash"], password):
            error = "Invalid phone number or password"
        else:
            session["user_id"] = str(user["_id"])
            return redirect(url_for("home_upcoming"))

    return render_template("user-sign-in.html", error=error)


@app.route("/create-account", methods=["GET", "POST"])
def create_account():
    error = None

    if request.method == "POST":
        phone_number = request.form.get("phone_number", "").strip()
        password = request.form.get("password", "")
        name = request.form.get("name", "").strip()

        if not phone_number or not password or not name:
            error = "Please fill in all fields."
        else:
            users = get_users_collection()

            existing_user = users.find_one({"phone_number": phone_number})

            if existing_user:
                error = "User already exists"
            else:
                users.insert_one(
                    {
                        "name": name,
                        "phone_number": phone_number,
                        "password_hash": generate_password_hash(password),
                        "lateness": [],
                        "events_owned": [],
                        "event_invites": [],
                    }
                )

                return redirect(url_for("sign_in"))

    return render_template("user-create-account.html", error=error)


@app.route("/home-past")
def home_past():
    return render_template("home-past.html")


@app.route("/home-upcoming")
def home_upcoming():
    return render_template("home-upcoming.html")


@app.route("/invites")
def invites():
    return render_template("invites.html")


@app.route("/host-events")
def host_events():
    return render_template("host-events.html")


# User dashboard route
@app.route("/user", methods=["GET", "POST"])
def user_dashboard():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("sign_in"))

    users = get_users_collection()
    user = users.find_one({"_id": ObjectId(user_id)})
    if not user:
        session.clear()
        return redirect(url_for("sign_in"))

    error = None
    message = None

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone_number = request.form.get("phone_number", "").strip()
        password = request.form.get("password", "")

        update_data = {}
        if name:
            update_data["name"] = name
        if phone_number:
            update_data["phone_number"] = phone_number
        if password:
            update_data["password_hash"] = generate_password_hash(password)

        if update_data:
            users.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
            user = users.find_one({"_id": ObjectId(user_id)})
            message = "Saved"
        else:
            error = "No changes to save"

    return render_template(
        "user-dashboard.html",
        user=user,
        error=error,
        message=message,
    )


@app.route("/sign-out")
def sign_out():
    session.clear()
    return redirect(url_for("sign_in"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)