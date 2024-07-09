import os
import subprocess

import flask
from flask import Flask, render_template, redirect, request
from flask_httpauth import HTTPBasicAuth
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from plot import *
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import psycopg2
from environment import DB_PASS
from pytz import timezone
import numpy as np
import json
import base64
import jwt
from functools import wraps


app = Flask(__name__)
auth = HTTPBasicAuth()

users = {
    "guest": generate_password_hash("chcividettisk"),
}

SECRET = "hahatajne"


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]

        if not token:
            return {"message": "Token is missing."}, 401

        try:
            if token == "token":
                return f({"username": "Nepřihlášen", "admin": False}, *args, **kwargs)
            user = jwt.decode(token, SECRET, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return {"message": 'Token has expired!'}, 401
        except jwt.InvalidTokenError:
            return {"message": 'Invalid token!'}, 401

        return f(user, *args, **kwargs)

    return decorated


@auth.verify_password
def verify_password(username, password):
    if username in users:
        if check_password_hash(users.get(username), password):
            return username


def select_timedelta(
    start=(datetime.utcnow() - timedelta(days=30)), end=datetime.utcnow()
):
    conn = psycopg2.connect(
        database="postgres",
        user="postgres",
        password=DB_PASS,
        host="89.221.216.28",
    )
    df = pd.read_sql(
        "SELECT * FROM weatherstation.records WHERE station_name = 'CBHOME' and inserted_at BETWEEN %(start)s AND %(end)s",
        conn,
        params={"start": start, "end": end},
    )
    if not df.empty:
        df["inserted_at"] = (
            df["inserted_at"].dt.tz_localize("utc").dt.tz_convert("Europe/Prague")
        )
        df = df.sort_values(by=["inserted_at"], axis=0, ascending=True)
        df["rain"] = df["rain"].apply(
            lambda row: None if row is None else 0 if row != 0 and (row / abs(row)) < 0 else row
        )
    return df


def select_last_record():
    conn = psycopg2.connect(
        database="postgres",
        user="postgres",
        password=DB_PASS,
        host="89.221.216.28",
    )
    df_last_record = pd.read_sql(
        "SELECT * FROM weatherstation.records WHERE station_name = 'CBHOME' and inserted_at=(SELECT max(inserted_at) FROM weatherstation.records where station_name = 'CBHOME');",
        conn,
    )
    df_last_record["inserted_at"] = (
        df_last_record["inserted_at"]
        .dt.tz_localize("utc")
        .dt.tz_convert("Europe/Prague")
    )

    if not df_last_record["rain"].isnull().all():
        df_last_record["rain"] = df_last_record["rain"].apply(
            lambda row: 0 if row != 0 and (row / abs(row)) < 0 else row
        )
    return df_last_record


def select_last_record_print():
    conn = psycopg2.connect(
        database="postgres",
        user="postgres",
        password=DB_PASS,
        host="89.221.216.28",
    )
    df_last_record = pd.read_sql(
        "SELECT * FROM tisk.records WHERE inserted_at=(SELECT max(inserted_at) FROM tisk.records);",
        conn,
    )

    df_last_record["inserted_at"] = (
        df_last_record["inserted_at"]
        .dt.tz_localize("utc")
        .dt.tz_convert("Europe/Prague")
    )

    return df_last_record


def select_timedelta_print(
    start=(datetime.utcnow() - timedelta(days=1)), end=datetime.utcnow()
):
    conn = psycopg2.connect(
        database="postgres",
        user="postgres",
        password=DB_PASS,
        host="89.221.216.28",
    )
    df = pd.read_sql(
        "SELECT * FROM tisk.records WHERE inserted_at BETWEEN %(start)s AND %(end)s",
        conn,
        params={"start": start, "end": end},
    )

    if not df.empty:
        df["inserted_at"] = (
            df["inserted_at"].dt.tz_localize("utc").dt.tz_convert("Europe/Prague")
        )
        df = df.sort_values(by=["inserted_at"], axis=0, ascending=True)

    return df


def create_list(df, df_day, df_week, df_month, value):
    if value == "pressure_bmp280":
        return [
            (df_day[value].max() / 100),
            (df_day[value].min() / 100),
            (df_week[value].max() / 100),
            (df_week[value].min() / 100),
            (df_month[value].max() / 100),
            (df_month[value].min() / 100),
            (df[value].max() / 100),
            (df[value].min() / 100),
        ]
    elif value == "rain":
        preklop_koef = 0.08
        return [
            (df_day[value].max() * preklop_koef),
            (df_day[value].min() * preklop_koef),
            (df_week[value].max() * preklop_koef),
            (df_week[value].min() * preklop_koef),
            (df_month[value].max() * preklop_koef),
            (df_month[value].min() * preklop_koef),
            (df[value].max() * preklop_koef),
            (df[value].min() * preklop_koef),
        ]
    else:
        return [
            df_day[value].max(),
            df_day[value].min(),
            df_week[value].max(),
            df_week[value].min(),
            df_month[value].max(),
            df_month[value].min(),
            df[value].max(),
            df[value].min(),
        ]


def read_content(sub_path: str):
    with open(f"content/{sub_path}.html", "r", encoding="utf-8") as f:
        return f.read()


def input_to_datetime(start_date, start_time, end_date, end_time):
    cet = timezone("Europe/Prague")
    if start_date is not None and end_date is not None:
        if (
            start_time is not None
            and end_time is not None
            and start_time != ""
            and end_time != ""
        ):
            start_date += f"T{start_time}"
            end_date += f"T{end_time}"
            if start_date == end_date:
                return datetime.now(timezone("utc")) - timedelta(days=30), datetime.now(
                    timezone("utc")
                )
            try:
                start_date = cet.localize(
                    datetime.strptime(start_date, "%Y-%m-%dT%H:%M")
                )
                end_date = cet.localize(datetime.strptime(end_date, "%Y-%m-%dT%H:%M"))
                if end_date > start_date:
                    return start_date, end_date
                else:
                    return (
                        datetime.now(timezone("utc")) - timedelta(days=30),
                        datetime.now(timezone("utc")),
                    )
            except ValueError:
                return (
                    datetime.now(timezone("utc")) - timedelta(days=30),
                    datetime.now(timezone("utc")),
                )
        else:
            try:
                start_date = cet.localize(
                    datetime.strptime(f"{start_date}T00:00", "%Y-%m-%dT%H:%M")
                )
                end_date = cet.localize(
                    datetime.strptime(f"{end_date}T23:59", "%Y-%m-%dT%H:%M")
                )
                if end_date > start_date:
                    return start_date, end_date
                else:
                    return (
                        datetime.now(timezone("utc")) - timedelta(days=30),
                        datetime.now(timezone("utc")),
                    )
            except ValueError:
                return datetime.now(timezone("utc")) - timedelta(days=30), datetime.now(
                    timezone("utc")
                )
    else:
        return datetime.now(timezone("utc")) - timedelta(days=30), datetime.now(
            timezone("utc")
        )


def hour_rain(df):
    if df.empty:
        return df
    df_hour = pd.DataFrame(df.groupby(pd.Grouper(key="inserted_at", freq="1H"))["rain"].sum())
    df_hour = pd.DataFrame({"inserted_at": df_hour.index, "rain": np.ravel(df_hour.values)})
    df_hour["inserted_at"] = df_hour["inserted_at"] + timedelta(hours=1)
    return df_hour


def day_rain(df):
    if df.empty:
        return df
    df_day = pd.DataFrame(df.groupby(pd.Grouper(key="inserted_at", freq="1D"))["rain"].sum())
    df_day = pd.DataFrame({"inserted_at": df_day.index, "rain": np.ravel(df_day.values)})
    df_day["inserted_at"] = df_day["inserted_at"] + timedelta(days=1)
    df_day = pd.concat([df_day, pd.DataFrame.from_dict({"inserted_at": df_day["inserted_at"].min() - timedelta(days=1),
                                                        "rain": [0]})], ignore_index=True)
    df_day = df_day.sort_values(by=["inserted_at"], axis=0, ascending=True)
    return df_day


def get_user_datetime_input():
    date_args = [
        request.args.get("start-date"),
        request.args.get("start-time"),
        request.args.get("end-date"),
        request.args.get("end-time"),
    ]
    for i in range(len(date_args)):
        if date_args[i] is None:
            date_args[i] = ""

    start_date, end_date = input_to_datetime(
        date_args[0],
        date_args[1],
        date_args[2],
        date_args[3],
    )
    return date_args, start_date, end_date


def get_datasets(start_date, end_date):
    df = select_timedelta(start_date, end_date)
    df_day = select_timedelta(
        (datetime.utcnow() - timedelta(days=1)), datetime.utcnow()
    )
    df_week = select_timedelta(
        (datetime.utcnow() - timedelta(days=7)), datetime.utcnow()
    )
    df_month = select_timedelta(
        (datetime.utcnow() - timedelta(days=30)), datetime.utcnow()
    )
    df_all_time = select_timedelta(
        datetime(year=2000, month=1, day=1), datetime.utcnow()
    )
    df_last_record = select_last_record()
    return df, df_day, df_week, df_month, df_all_time, df_last_record


HOME = read_content("home")
INFO = read_content("info")
RAIN = read_content("rain")
RADIO = read_content("radio")
CAM = read_content("cam")


@app.route("/")
def index():
    return redirect("/home")


@app.route("/home")
def home():
    date_args, start_date, end_date = get_user_datetime_input()
    df = select_timedelta(start_date, end_date)
    df_last_record = select_last_record()
    return render_template(
        "template.html",
        date_args=date_args,
        title="Home",
        content=HOME,
        plot=create_plot_main(df, "main-plot"),
        form=render_template(
            "form.html",
            today_date=f"'{datetime.now(timezone('Europe/Prague')).strftime('%Y-%m-%d')}'",
        ),
        table=create_table_main(
            (
                df_last_record["inserted_at"].max(),
                df_last_record["temperature_bmp280"].round(2) if not df_last_record["temperature_bmp280"].isnull().any() else None,
                df_last_record["temperature_ds18b20"].round(2) if not df_last_record["temperature_ds18b20"].isnull().any() else None,
                (df_last_record["pressure_bmp280"] / 100).round(2) if not df_last_record["pressure_bmp280"].isnull().any() else None,
                df_last_record["rain"] * 0.08 if not df_last_record["rain"].isnull().any() else None,
                df_last_record["humidity_dht"],
                df_last_record["light_bh1750"].round(2) if not df_last_record["light_bh1750"].isnull().any() else None,
            ),
            "recent-main",
        ),
        page_id=0,
    )


@app.route("/rain")
def rain():
    date_args, start_date, end_date = get_user_datetime_input()
    df, df_day, df_week, df_month, df_all_time, df_last_record = get_datasets(start_date, end_date)
    df_hour_rain = hour_rain(df)
    df_day_rain = day_rain(df)
    return render_template(
        "template.html",
        date_args=date_args,
        content=RAIN,
        title="Srážky",
        plot=create_plot_rain(df, "rain-plot-min")
        + create_plot_rain(df_hour_rain, "rain-plot-hour")
        + create_plot_rain(df_day_rain, "rain-plot-day"),
        table=create_table(
            create_list(df_all_time, df_day, df_week, df_month, "rain"),
            "rain-table",
            "mm/5min",
        ),
        form=render_template(
            "form.html",
            today_date=f"'{datetime.now(timezone('Europe/Prague')).strftime('%Y-%m-%d')}'",
            radio=RADIO,
        ),
        table_recent=create_table_recent(
            (
                "Aktuálně(mm/5min)",
                df_last_record["rain"] * 0.08 if not df_last_record["rain"].isnull().any() else None,
                df_last_record["inserted_at"].max(),
            ),
            "recent-rain",
        ),
        page_id=1,
    )


@app.route("/press")
def press():
    date_args, start_date, end_date = get_user_datetime_input()
    df, df_day, df_week, df_month, df_all_time, df_last_record = get_datasets(start_date, end_date)
    return render_template(
        "template.html",
        date_args=date_args,
        title="Tlak",
        plot=create_plot_press(df, "press-plot"),
        table=create_table(
            create_list(df_all_time, df_day, df_week, df_month, "pressure_bmp280"),
            "press-table",
            "hPa",
        ),
        form=render_template(
            "form.html",
            today_date=f"'{datetime.now(timezone('Europe/Prague')).strftime('%Y-%m-%d')}'",
        ),
        table_recent=create_table_recent(
            (
                "Aktuálně(hPa)",
                (df_last_record["pressure_bmp280"] / 100).round(2) if not df_last_record["pressure_bmp280"].isnull().any() else None,
                df_last_record["inserted_at"].max(),
            ),
            "recent-press",
        ),
        page_id=2,
    )


@app.route("/temp")
def temp():
    date_args, start_date, end_date = get_user_datetime_input()
    df, df_day, df_week, df_month, df_all_time, df_last_record = get_datasets(start_date, end_date)
    return render_template(
        "template.html",
        date_args=date_args,
        title="Teplota",
        plot=create_plot_temp(df, "temp-plot"),
        table=create_table(
            create_list(df_all_time, df_day, df_week, df_month, "temperature_bmp280"),
            "temp-table",
            "Teploměr °C",
        )
        + create_table(
            create_list(df_all_time, df_day, df_week, df_month, "temperature_ds18b20"),
            "temp2-table",
            "Teploměr (balkon) °C",
        ),
        form=render_template(
            "form.html",
            today_date=f"'{datetime.now(timezone('Europe/Prague')).strftime('%Y-%m-%d')}'",
        ),
        table_recent=create_table_recent(
            (
                "Aktuálně(°C)",
                df_last_record["temperature_ds18b20"].round(2) if not df_last_record["temperature_ds18b20"].isnull().any() else None,
                df_last_record["inserted_at"].max(),
            ),
            "recent-temp",
        ),
        page_id=3,
    )


@app.route("/humi")
def humi():
    date_args, start_date, end_date = get_user_datetime_input()
    df, df_day, df_week, df_month, df_all_time, df_last_record = get_datasets(start_date, end_date)
    return render_template(
        "template.html",
        date_args=date_args,
        title="Vlhkost",
        plot=create_plot_humi(df, "humi-plot"),
        table=create_table(
            create_list(df_all_time, df_day, df_week, df_month, "humidity_dht"),
            "humi-table",
            "%",
        ),
        form=render_template(
            "form.html",
            today_date=f"'{datetime.now(timezone('Europe/Prague')).strftime('%Y-%m-%d')}'",
        ),
        table_recent=create_table_recent(
            (
                "Aktuálně(%)",
                df_last_record["humidity_dht"],
                df_last_record["inserted_at"].max(),
            ),
            "recent-humi",
        ),
        page_id=4,
    )


@app.route("/info")
def info():
    date_args, _, _ = get_user_datetime_input()
    active_sensors = ""
    human_readable_sensors = {
        "temperature_ds18b20": "Teplota (balkon)",
        "temperature_bmp280": "Teplota (meteostanice)",
        "humidity_dht": "Relativní vlhkost vzduchu",
        "pressure_bmp280": "Tlak",
        "rain": "Srážky",
        "anemometer": "Rychlost větru",
        "light_bh1750": "Intenzita světla",
        "solar": "Osvícení (solarní panel)",
    }
    for key, value in get_active_sensors().items():
        if key in human_readable_sensors:
            if value:
                active_sensors += f"{human_readable_sensors[key]}: "
                active_sensors += '<em style = "color: green;font-style: normal;font-weight: 700;"> Aktivní </em> <br>'
            else:
                active_sensors += f"{human_readable_sensors[key]}: "
                active_sensors += '<em style = "color: red;font-style: normal;font-weight: 700;"> Neaktivní </em> <br>'

    table_replacement_content = f"<img src='/static/meteostanice.png' style='width:384px;height:216px;float: right;'>" \
                                f"<br>" \
                                f"<div style='margin:65px; display:inline-block'><h1 style='font-size: 1.1em'> Aktuální aktivita čidel </h1><br>{active_sensors}</div>"

    return render_template(
        "template.html",
        date_args=date_args,
        content=INFO,
        title="Info",
        table=table_replacement_content,
        page_id=5,
    )


@app.route("/api/v1/weather/<int:hours>")
def weather(hours):
    df = select_timedelta(
        (datetime.utcnow() - timedelta(hours=hours)), datetime.utcnow()
    )
    df["inserted_at"] = df["inserted_at"].apply(lambda x: x.value / 1000000)
    df = df.where(pd.notnull(df), None)
    df = df.reset_index().to_dict(orient="list")
    return df


@app.route("/api/v1/weather/last")
def weather_last():
    df = select_last_record()
    df["formatted_date"] = df["inserted_at"].max().strftime('%Y-%m-%d %H:%M')
    df["inserted_at"] = df["inserted_at"].apply(lambda x: x.value / 1000000)
    df = df.where(pd.notnull(df), None)
    df = df.reset_index().to_dict(orient="list")
    return df


@app.route("/api/v1/printer/<int:hours>")
def get_printer_values(hours):
    df = select_timedelta_print(
        (datetime.utcnow() - timedelta(hours=hours)), datetime.utcnow()
    )
    return json.dumps(
        [
            df["temperature"].tolist(),
            df["humidity"].tolist(),
            df["inserted_at"].apply(lambda x: x.value / 1000000).tolist(),
        ]
    )


@app.route("/api/v1/printer/current")
def get_printer_values_current():
    df = select_last_record_print()
    return json.dumps(
        [
            df["temperature"][0],
            df["humidity"][0],
            df["inserted_at"][0].strftime('%Y-%m-%d %H:%M'),
        ]
    )


@app.route("/weatherstation/set_active_sensors")
def set_active_sensors():
    with open("sensors.json", "r") as f:
        sensors = json.load(f)
        f.close()
    sensor_states = ["checked" if sensors[sensor] else "" for sensor in sensors]

    if request.args.get("send_to_server", False, type=bool):
        new_sensor_states = {}
        for sensor in sensors:
            new_sensor_states[sensor] = request.args.get(sensor, False, type=bool)
        with open("sensors.json", "w") as f:
            json.dump(new_sensor_states, f)
            f.close()

    return render_template(
        "sensors_form.html",
        sensors=sensor_states,
    )


@app.route("/weatherstation/get_active_sensors")
def get_active_sensors():
    with open("sensors.json", "r") as f:
        sensors = json.load(f)
    return sensors


@app.route("/printer")
def get_printer_info():
    hours = request.args.get("hours")
    return render_template("printer.html", hours=hours if hours is not None else 5)


@app.route('/printer/set_info', methods=['GET'])
def set_printer_values():
    if request.method == 'GET':
        with open("static/printer.json", "w") as f:
            json.dump(request.json, f)
            f.close()
        return "OK"
    return "KO"


@app.errorhandler(404)
def page_not_found(error):
    return (
        render_template(
            "template.html",
            content="<h1>Tuto stránku jsme bohužel nenalezli</h1>",
            title="Error 404",
        ),
        404,
    )


@app.route('/cam/upload', methods=['POST'])
def cam_upload():
    if request.method == 'POST':
        path_to_images = Path("images")
        now = datetime.utcnow()
        sent_by, save = request.form["meta"].split(" ")
        with open("static/printer.json", "r") as f:
            printer = json.load(f)
            f.close()
        job_name = printer["file"]["display_name"]
        if sent_by == "WEB":
            job_name = "manual"
        filename = path_to_images / secure_filename(f"{job_name}_{sent_by.lower()}_{now.strftime('%Y_%m_%d_%H_%M_%S')}.jpg")
        request.files["image"].save(filename)
        subprocess.run(f"cp {filename} static/latest.jpg", shell=True, text=True)
        if sent_by != "WEB" and save == "1":
            result = subprocess.run(f"mega-put {filename.absolute()} PrinterImages", shell=True, text=True)
        os.remove(filename)
        return "OK"

    return "KO"


@app.route('/cam/stream', methods=['GET'])
@auth.login_required
def cam_stream():
    return CAM


@app.route('/cam/stream/image', methods=['GET'])
@auth.login_required
def cam_stream_image():
    json_data = {}

    with open("static/latest.jpg", "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
        json_data["image"] = encoded_string.decode("utf-8")
    json_data["image_date"] = datetime.fromtimestamp(os.path.getmtime("static/latest.jpg")).strftime("%Y-%m-%d %H:%M:%S")
    with open("static/printer.json", "r") as f:
        printer = json.load(f)
        f.close()
    json_data["job_name"] = printer["file"]["display_name"]
    json_data["time_remaining"] = printer["time_remaining"]
    json_data["time_printing"] = printer["time_printing"]
    json_data["progress"] = printer["progress"]

    return json.dumps(json_data)


@app.route('/climbing/random', methods=['GET'])
def climbing_random():
    conn = psycopg2.connect(
        database="postgres",
        user="postgres",
        password=DB_PASS,
        host="89.221.216.28",
    )
    df = pd.read_sql(
        "SELECT * FROM climbing.boulders",
        conn,
    )

    html_counts_unordered_list = "<ul>"
    by_angle = df.groupby("angle")
    data = {}
    for angle, a_group in by_angle:
        html_counts_unordered_list += f"<li>{angle}˚: {len(a_group)}</li><ul>"
        by_grade = a_group.groupby("grade")
        data[angle] = {}
        for grade, g_group in by_grade:
            html_counts_unordered_list += f"<li>V{grade}: {len(g_group)}</li>"
            g_group["name"] = g_group["name"].apply(lambda x: x.replace('"', '\\"'))
            data[angle][grade] = g_group.to_dict(orient="records")
        html_counts_unordered_list += "</ul>"
    html_counts_unordered_list += "</ul>"

    return render_template("random_boulder.html", boulders=json.dumps(data), n_boulders=html_counts_unordered_list)


@app.route('/climbing/boulders/<int:angle>', methods=['GET'])
@token_required
def climbing_boulders(current_user, angle):
    conn = psycopg2.connect(
        database="postgres",
        user="postgres",
        password=DB_PASS,
        host="89.221.216.28",
    )
    angle = int(angle)

    df = pd.read_sql(
        f"""
            SELECT
                b.id,
                b.name,
                b.description,
                b.build_time,
                b.built_by,
                COALESCE(AVG(s.grade), -1) as average_grade,
                COALESCE(AVG(s.rating), -1) as average_rating,
                CASE
                    WHEN COUNT(u.name) > 0 THEN TRUE
                    ELSE FALSE
                END as sent,
                CASE
                    WHEN f.name IS NOT NULL THEN TRUE
                    ELSE FALSE
                END as favourite
            FROM
                climbing.boulders b
            LEFT JOIN
                climbing.sends s ON b.id = s.boulder_id AND s.angle = {angle}
            LEFT JOIN
                climbing.users u ON u.id = s.user_id AND u.name = '{current_user["username"]}'
            LEFT JOIN
                (SELECT f.boulder_id, u.name from climbing.favourites f JOIN climbing.users u ON f.user_id = u.id) f
            ON
                b.id = f.boulder_id AND f.name = '{current_user["username"]}'
            GROUP BY
                b.id, b.name, f.name;
        """,
        conn,
    )

    return df.to_json(orient="records")


@app.route('/climbing/boulders/detail/<int:bid>', methods=['POST'])
def climbing_boulders_detail(bid):
    conn = psycopg2.connect(
        database="postgres",
        user="postgres",
        password=DB_PASS,
        host="89.221.216.28",
    )

    df = pd.read_sql(
        f"SELECT hold_id, hold_type, path FROM climbing.boulders JOIN climbing.boulder_holds ON climbing.boulders.id = climbing.boulder_holds.boulder_id JOIN climbing.holds ON climbing.holds.id = climbing.boulder_holds.hold_id WHERE climbing.boulders.id = {bid}",
        conn,
    )

    return df.to_json(orient="records")


@app.route('/climbing/wall', methods=['GET'])
def climbing_wall():
    with open("static/stena.jpg", "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
        return encoded_string.decode("utf-8")


@app.route('/climbing/holds', methods=['GET'])
def climbing_holds():
    conn = psycopg2.connect(
        database="postgres",
        user="postgres",
        password=DB_PASS,
        host="89.221.216.28",
    )
    df = pd.read_sql(
        f"SELECT id, path FROM climbing.holds",
        conn,
    )

    return df.to_json(orient="records")


@app.route('/climbing/signup', methods=['POST'])
def climbing_signup():
    data = request.get_json()
    username = data["username"]
    password = data["password"]
    hashed_password = generate_password_hash(password)

    # Check if user already exists (username is unique)
    conn = psycopg2.connect(
        database="postgres",
        user="postgres",
        password=DB_PASS,
        host="89.221.216.28",
    )

    df = pd.read_sql(
        f"SELECT name FROM climbing.users",
        conn,
    )

    if username in df["name"].values:
        return f"Uživatel s jménem {username} již existuje.", 400

    cur = conn.cursor()
    cur.execute(
        f"INSERT INTO climbing.users (name, password) VALUES ('{username}', '{hashed_password}')",
    )

    conn.commit()
    cur.close()
    conn.close()
    return f"Uživatel {username} byl úspěšně vytvořen.", 200


@app.route('/climbing/login', methods=['POST'])
def climbing_login():
    data = request.get_json()
    username = data["username"]
    password = data["password"]

    conn = psycopg2.connect(
        database="postgres",
        user="postgres",
        password=DB_PASS,
        host="89.221.216.28",
    )

    # Get user from db
    cur = conn.cursor()
    cur.execute(
        f"SELECT password, admin FROM climbing.users WHERE name = '{username}'",
    )

    user_data = cur.fetchone()

    cur.close()
    conn.close()

    if user_data is not None:
        if check_password_hash(user_data[0], password):
            token = jwt.encode({"username": username, "admin": user_data[1]}, SECRET, algorithm="HS256")
            return token, 200
        else:
            return "Špatné heslo.", 401

    return f"Uživatel {username} neexistuje.", 400


@app.route('/climbing/whoami', methods=['GET'])
@token_required
def climbing_whoami(current_user):
    return current_user, 200


@app.route('/climbing/log_send', methods=['POST'])
@token_required
def climbing_log_send(current_user):
    if current_user["username"] == "Nepřihlášen":
        return "Musíte být přihlášen.", 401

    print(current_user)

    data = request.get_json()
    print(data)
    boulder_id = data["boulder_id"]
    grade = data["grade"]
    rating = data["rating"]
    angle = data["angle"]
    attempts = data["attempts"]

    if boulder_id is None or grade is None or rating is None or angle is None or attempts is None:
        return "Něco chybí.", 400

    conn = psycopg2.connect(
        database="postgres",
        user="postgres",
        password=DB_PASS,
        host="89.221.216.28",
    )

    # Insert send into db
    cur = conn.cursor()
    cur.execute(
        f"""
        INSERT INTO
            climbing.sends (user_id, boulder_id, grade, rating, angle, attempts, sent_date)
        VALUES
            (
                (SELECT id FROM climbing.users WHERE name = '{current_user['username']}'),
                {boulder_id},
                {grade},
                {rating},
                {angle},
                {attempts},
                NOW()
                )
        """,
    )

    conn.commit()
    cur.close()
    conn.close()

    return "OK", 200
