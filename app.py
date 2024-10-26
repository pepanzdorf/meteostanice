import os
import subprocess

import flask
from flask import Flask, render_template, redirect, request
from flask_httpauth import HTTPBasicAuth
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from plot import *
from climbing_functions import *
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


db_conn = {
    "database": "postgres",
    "user": "postgres",
    "password": DB_PASS,
    "host": "89.221.216.28",
}


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
        **db_conn
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
        **db_conn
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
        **db_conn
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
        **db_conn
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
PATCH_100 = read_content("patch_1.0.0")
PATCH_101 = read_content("patch_1.0.1")
PATCH_110 = read_content("patch_1.1.0")
PATCH_111 = read_content("patch_1.1.1")
PATCH_112 = read_content("patch_1.1.2")
PATCH_113 = read_content("patch_1.1.3")
PATCH_114 = read_content("patch_1.1.4")
PATCH_115 = read_content("patch_1.1.5")
PATCH_116 = read_content("patch_1.1.6")
PATCH_120 = read_content("patch_1.2.0")
PATCH_121 = read_content("patch_1.2.1")
PATCH_122 = read_content("patch_1.2.2")
PATCH_123 = read_content("patch_1.2.3")
PATCH_124 = read_content("patch_1.2.4")
PATCH_125 = read_content("patch_1.2.5")
PATCH_126 = read_content("patch_1.2.6")


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
        **db_conn
    )
    angle = int(angle)

    time_now = datetime.now()
    if time_now.month <= 5:
        season_start = datetime(time_now.year, 1, 1)
        season_end = datetime(time_now.year, 5, 31)
    else:
        season_start = datetime(time_now.year, 6, 1)
        season_end = datetime(time_now.year, 12, 31)

    df = pd.read_sql(
        """
            SELECT
                b.id,
                b.name,
                b.description,
                b.build_time,
                (SELECT name FROM climbing.users WHERE id = b.built_by) as built_by,
                ROUND(bg.average_grade) as average_grade,
                bg.average_rating as average_rating,
                CASE
                    WHEN COUNT(u.name) > 0 THEN TRUE
                    ELSE FALSE
                END as sent,
                CASE
                    WHEN COUNT(u.name) FILTER (WHERE s.sent_date BETWEEN %(season_start)s AND %(season_end)s) > 0 THEN TRUE
                    ELSE FALSE
                END as sent_season,
                CASE
                    WHEN f.name IS NOT NULL THEN TRUE
                    ELSE FALSE
                END as favourite,
                tb.tags
            FROM
                climbing.boulders b
            JOIN
                climbing.boulder_grades bg ON b.id = bg.id
            LEFT JOIN
                climbing.sends s ON b.id = s.boulder_id AND s.angle = %(angle)s
            LEFT JOIN
                climbing.users u ON u.id = s.user_id AND u.name = %(username)s
            LEFT JOIN
                (SELECT f.boulder_id, u.name from climbing.favourites f JOIN climbing.users u ON f.user_id = u.id) f
            ON
                b.id = f.boulder_id AND f.name = %(username)s
            LEFT JOIN
                climbing.tags_by_boulder tb ON b.id = tb.boulder_id
            GROUP BY
                b.id, b.name, f.name, bg.average_grade, bg.average_rating, tb.tags;
        """,
        conn,
        params={"angle": angle, "username": current_user["username"], 'season_start': season_start, 'season_end': season_end},
    )

    return df.to_json(orient="records")


@app.route('/climbing/boulders/sends/<int:bid>', methods=['POST'])
def climbing_boulders_sends(bid):
    data = request.get_json()
    angle = data["angle"]

    conn = psycopg2.connect(
        **db_conn
    )

    df = pd.read_sql(
        f"SELECT s.id, grade, sent_date, attempts, rating, name, challenge_id FROM climbing.sends s JOIN climbing.users u ON s.user_id = u.id WHERE s.boulder_id = %(bid)s AND s.angle = %(angle)s ORDER BY s.sent_date DESC",
        conn,
        params={"bid": bid, "angle": angle},
    )

    return df.to_json(orient="records")


@app.route('/climbing/boulders/holds/<int:bid>', methods=['GET'])
def climbing_boulders_holds(bid):
    conn = psycopg2.connect(
        **db_conn
    )

    df = pd.read_sql(
        f"SELECT hold_id, hold_type, path, is_volume FROM climbing.boulders JOIN climbing.boulder_holds ON climbing.boulders.id = climbing.boulder_holds.boulder_id JOIN climbing.holds ON climbing.holds.id = climbing.boulder_holds.hold_id WHERE climbing.boulders.id = %(bid)s ORDER BY climbing.holds.id",
        conn,
        params={"bid": bid},
    )

    if df.empty:
        return {"false": [], "true": []}

    grouped_dict = df.groupby("is_volume").apply(lambda x: x.to_dict(orient="records")).to_dict()
    grouped_dict = {str(key).lower(): value for key, value in grouped_dict.items()}

    if 'true' not in grouped_dict.keys():
        grouped_dict["true"] = []
    if 'false' not in grouped_dict.keys():
        grouped_dict["false"] = []

    return grouped_dict


@app.route('/climbing/wall', methods=['GET'])
def climbing_wall():
    with open("static/stena.jpg", "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
        return encoded_string.decode("utf-8")


@app.route('/climbing/holds', methods=['GET'])
def climbing_holds():
    conn = psycopg2.connect(
        **db_conn
    )
    df = pd.read_sql(
        f"""
        SELECT
            climbing.holds.id, path, is_volume, types_counts, boulders
        FROM climbing.holds
        JOIN climbing.hold_counts ON climbing.holds.id = climbing.hold_counts.id
        JOIN climbing.hold_boulders ON climbing.hold_boulders.id = climbing.holds.id ORDER BY climbing.holds.id
        """,
        conn,
    )

    if df.empty:
        return {"false": [], "true": []}

    grouped_dict = df.groupby("is_volume").apply(lambda x: x.to_dict(orient="records")).to_dict()
    grouped_dict = {str(key).lower(): value for key, value in grouped_dict.items()}

    if 'true' not in grouped_dict.keys():
        grouped_dict["true"] = []
    if 'false' not in grouped_dict.keys():
        grouped_dict["false"] = []

    return grouped_dict


@app.route('/climbing/signup', methods=['POST'])
def climbing_signup():
    data = request.get_json()
    username = data["username"]
    password = data["password"]
    hashed_password = generate_password_hash(password)

    # Check if user already exists (username is unique)
    conn = psycopg2.connect(
        **db_conn
    )

    df = pd.read_sql(
        f"SELECT name FROM climbing.users",
        conn,
    )

    if username in df["name"].values:
        return f"Uživatel s jménem {username} již existuje.", 400

    cur = conn.cursor()
    cur.execute(
        f"INSERT INTO climbing.users (name, password) VALUES (%(username)s, %(hashed_password)s)",
        {"username": username, "hashed_password": hashed_password},
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
        **db_conn
    )

    # Get user from db
    cur = conn.cursor()
    cur.execute(
        f"SELECT password, admin FROM climbing.users WHERE name = %(username)s",
        {"username": username},
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
    if current_user["username"] == "Nepřihlášen":
        return {"username": "Nepřihlášen", "admin": False, "description": ""}, 200
    else:
        conn = psycopg2.connect(
            **db_conn
        )

        cur = conn.cursor()
        cur.execute(
            f"SELECT description FROM climbing.users WHERE name = %(username)s",
            {"username": current_user["username"]},
        )

        description = cur.fetchone()

        cur.close()
        conn.close()

        return {"username": current_user["username"], "admin": current_user["admin"], "description": description[0]}, 200


@app.route('/climbing/log_send', methods=['POST'])
@token_required
def climbing_log_send(current_user):
    if current_user["username"] == "Nepřihlášen":
        return "Musíte být přihlášen.", 401

    data = request.get_json()
    boulder_id = data["boulder_id"]
    grade = data["grade"]
    rating = data["rating"]
    angle = data["angle"]
    attempts = data["attempts"]
    challenge = data["challenge"]

    if boulder_id is None or grade is None or rating is None or angle is None or attempts is None or challenge is None:
        return "Něco chybí.", 400

    conn = psycopg2.connect(
        **db_conn
    )

    # Insert send into db
    cur = conn.cursor()
    cur.execute(
        f"""
        INSERT INTO
            climbing.sends (user_id, boulder_id, grade, rating, angle, attempts, sent_date, challenge_id)
        VALUES
            (
                (SELECT id FROM climbing.users WHERE name = %(username)s),
                %(boulder_id)s,
                %(grade)s,
                %(rating)s,
                %(angle)s,
                %(attempts)s,
                NOW(),
                %(challenge)s
                )
        """,
        {"username": current_user["username"], "boulder_id": boulder_id, "grade": grade, "rating": rating, "angle": angle, "attempts": attempts, "challenge": challenge}
    )

    conn.commit()
    cur.close()
    conn.close()

    return "OK", 200


@app.route('/climbing/boulders/favourite/<int:bid>', methods=['DELETE', 'POST'])
@token_required
def climbing_favourite(current_user, bid):
    if current_user["username"] == "Nepřihlášen":
        return "Musíte být přihlášen.", 401

    conn = psycopg2.connect(
        **db_conn
    )

    if request.method == 'DELETE':
        cur = conn.cursor()
        cur.execute(
            f"DELETE FROM climbing.favourites WHERE user_id = (SELECT id FROM climbing.users WHERE name = %(username)s) AND boulder_id = %(bid)s",
            {"username": current_user["username"], "bid": bid}
        )

        conn.commit()
        cur.close()
        conn.close()
        return "OK", 200

    if request.method == 'POST':
        cur = conn.cursor()
        cur.execute(
            f"INSERT INTO climbing.favourites (user_id, boulder_id) VALUES ((SELECT id FROM climbing.users WHERE name = %(username)s), %(bid)s)",
            {"username": current_user["username"], "bid": bid}
        )

        conn.commit()
        cur.close()
        conn.close()
        return "OK", 200


@app.route('/climbing/boulders/comments/<int:bid>', methods=['GET'])
def climbing_boulders_comments(bid):

    conn = psycopg2.connect(
        **db_conn
    )

    df = pd.read_sql(
        f"SELECT c.id, name, date, text FROM climbing.comments c JOIN climbing.users u ON c.user_id = u.id WHERE c.boulder_id = %(bid)s ORDER BY c.date DESC",
        conn,
        params={"bid": bid},
    )

    return df.to_json(orient="records")


@app.route('/climbing/boulders/comment/<int:bid>', methods=['POST'])
@token_required
def climbing_boulders_comment(current_user, bid):
    if current_user["username"] == "Nepřihlášen":
        return "Musíte být přihlášen.", 401

    data = request.get_json()
    text = data["text"]

    if text is None:
        return "Něco chybí.", 400

    conn = psycopg2.connect(
        **db_conn
    )

    cur = conn.cursor()
    cur.execute(
        f"INSERT INTO climbing.comments  (user_id, boulder_id, text, date) VALUES ((SELECT id FROM climbing.users WHERE name = %(username)s), %(bid)s, %(text)s, NOW())",
        {"username": current_user["username"], "bid": bid, "text": text}
    )

    conn.commit()
    cur.close()
    conn.close()

    return "OK", 200


@app.route('/climbing/boulders/comment/<int:cid>', methods=['DELETE'])
@token_required
def climbing_boulders_comment_delete(current_user, cid):
    if current_user["username"] == "Nepřihlášen":
        return "Musíte být přihlášen.", 401

    conn = psycopg2.connect(
        **db_conn
    )

    # Check if user is owner of the comment
    cur = conn.cursor()
    cur.execute(
        f"SELECT name FROM climbing.comments c JOIN climbing.users u ON c.user_id = u.id WHERE c.id = %(cid)s",
        {"cid": cid}
    )

    username = cur.fetchone()
    if username is None:
        return "Komentář neexistuje.", 404

    if username[0] != current_user["username"] and not current_user["admin"]:
        return "Nemáte oprávnění.", 403

    cur = conn.cursor()
    cur.execute(
        f"DELETE FROM climbing.comments WHERE id = %(cid)s",
        {"cid": cid}
    )

    conn.commit()
    cur.close()
    conn.close()

    return "OK", 200


@app.route('/climbing/boulders/send/<int:sid>', methods=['DELETE'])
@token_required
def climbing_boulders_send_delete(current_user, sid):
    if current_user["username"] == "Nepřihlášen":
        return "Musíte být přihlášen.", 401

    conn = psycopg2.connect(
        **db_conn
    )

    # Check if user is owner of the send
    cur = conn.cursor()
    cur.execute(
        f"SELECT name FROM climbing.sends s JOIN climbing.users u ON s.user_id = u.id WHERE s.id = %(sid)s",
        {"sid": sid}
    )

    username = cur.fetchone()
    if username is None:
        return "Výlez neexistuje.", 404


    if username[0] != current_user["username"] and not current_user["admin"]:
        return "Nemáte oprávnění.", 403


    cur = conn.cursor()
    cur.execute(
        f"DELETE FROM climbing.sends WHERE id = %(sid)s",
        {"sid": sid}
    )


    conn.commit()
    cur.close()
    conn.close()

    return "OK", 200


@app.route('/climbing/boulders/challenges', methods=['GET'])
def climbing_boulders_challenges():
    conn = psycopg2.connect(
        **db_conn
    )

    df = pd.read_sql(
        f"SELECT id, name, description, score FROM climbing.challenges WHERE id != 1 ORDER BY score",
        conn,
    )

    return df.to_json(orient="records")


@app.route('/climbing/challenges/completed/<int:bid>', methods=['POST'])
@token_required
def climbing_challenges_completed(current_user, bid):
    if current_user["username"] == "Nepřihlášen":
        return "Nepřihlášen", 401

    data = request.get_json()
    angle = data["angle"]

    conn = psycopg2.connect(
        **db_conn
    )

    df = pd.read_sql(
        f"SELECT DISTINCT s.challenge_id, c.name, c.score  FROM climbing.sends s JOIN climbing.challenges c ON s.challenge_id = c.id WHERE user_id = (SELECT id FROM climbing.users WHERE name = %(username)s) AND boulder_id = %(bid)s AND angle = %(angle)s AND s.challenge_id != 1",
        conn,
        params={"username": current_user["username"], "bid": bid, "angle": angle},
    )

    if df.empty:
        return "Žádné výzvy", 400

    return {'ids': df["challenge_id"].to_list(), 'rest': df.to_dict(orient="records")}


@app.route('/climbing/boulder', methods=['POST'])
@token_required
def save_boulder(current_user):
    data = request.get_json()
    name = data["name"]
    description = data["description"]
    holds = data["holds"]
    edit = data["edit"]
    bid = data["bid"]
    tags = data["tags"]

    if current_user["username"] == "Nepřihlášen":
        return "Musíte být přihlášen.", 401

    conn = psycopg2.connect(
        **db_conn
    )

    if edit:
        cur = conn.cursor()
        cur.execute(
            f"SELECT u.name FROM climbing.boulders b JOIN climbing.users u ON b.built_by = u.id WHERE b.id = %(bid)s",
            {"bid": bid}
        )

        username = cur.fetchone()
        if username is None:
            return "Boulder neexistuje.", 404

        if username[0] != current_user["username"] and not current_user["admin"]:
            return "Nemáte oprávnění.", 403

        cur.execute(
            f"UPDATE climbing.boulders SET name = %(name)s, description = %(description)s WHERE id = %(bid)s",
            {"name": name, "description": description, "bid": bid}
        )

        cur.execute(
            f"DELETE FROM climbing.boulder_holds WHERE boulder_id = %(bid)s",
            {"bid": bid}
        )

        cur.execute(
            f"DELETE FROM climbing.boulder_tags WHERE boulder_id = %(bid)s",
            {"bid": bid}
        )

        for tag in tags:
            if tag is not None:
                cur.execute(
                    f"INSERT INTO climbing.boulder_tags (boulder_id, tag_id) VALUES (%(bid)s, %(tag)s)",
                    {"bid": bid, "tag": tag}
                )

        for hold in holds:
            cur.execute(
                f"INSERT INTO climbing.boulder_holds (boulder_id, hold_id, hold_type) VALUES (%(bid)s, %(hold_id)s, %(hold_type)s)",
                {"bid": bid, "hold_id": hold["id"], "hold_type": hold["type"]}
            )

        conn.commit()
        cur.close()
        conn.close()

        return "EDITED", 200
    else:
        cur = conn.cursor()
        cur.execute(
            f"SELECT id FROM climbing.users WHERE name = %(username)s",
            {"username": current_user["username"]}
        )

        uid = cur.fetchone()[0]

        cur.execute(
            f"INSERT INTO climbing.boulders (name, description, build_time, built_by) VALUES (%(name)s, %(description)s, NOW(), %(uid)s) RETURNING id",
            {"name": name, "description": description, "uid": uid}
        )

        bid = cur.fetchone()[0]

        for tag in tags:
            if tag is not None:
                cur.execute(
                    f"INSERT INTO climbing.boulder_tags (boulder_id, tag_id) VALUES (%(bid)s, %(tag)s)",
                    {"bid": bid, "tag": tag}
                )

        for hold in holds:
            cur.execute(
                f"INSERT INTO climbing.boulder_holds (boulder_id, hold_id, hold_type) VALUES (%(bid)s, %(hold_id)s, %(hold_type)s)",
                {"bid": bid, "hold_id": hold["id"], "hold_type": hold["type"]}
            )

        conn.commit()
        cur.close()
        conn.close()

        return "SAVED", 200


@app.route('/climbing/boulders/<int:bid>', methods=['DELETE'])
@token_required
def boulder_delete(current_user, bid):
    if current_user["username"] == "Nepřihlášen":
        return "Musíte být přihlášen.", 401

    conn = psycopg2.connect(
        **db_conn
    )

    # Check if user is builder of the boulder
    cur = conn.cursor()
    cur.execute(
        f"SELECT u.name FROM climbing.boulders b JOIN climbing.users u ON b.built_by = u.id WHERE b.id = %(bid)s",
        {"bid": bid}
    )

    username = cur.fetchone()
    if username is None:
        return "Výlez neexistuje.", 404


    if username[0] != current_user["username"] and not current_user["admin"]:
        return "Nemáte oprávnění.", 403


    cur = conn.cursor()
    cur.execute(
        f"DELETE FROM climbing.boulders WHERE id = %(bid)s",
        {"bid": bid}
    )


    conn.commit()
    cur.close()
    conn.close()

    return "OK", 200


@app.route('/climbing/stats', methods=['POST'])
def climbing_stats():
    data = request.get_json()
    angle = data["angle"]

    conn = psycopg2.connect(
        **db_conn
    )

    df = pd.read_sql(
        """
            SELECT
                b.id as boulder_id,
                ROUND(average_grade) as grade,
                attempts,
                challenge_id,
                score,
                sent_date,
                u.name as username,
                u.icon_url as icon_url,
                u.description as user_description,
                u.border as border
            FROM
                climbing.boulders b
            JOIN
                climbing.boulder_grades bg ON b.id = bg.id AND bg.angle = %(angle)s
            JOIN
                climbing.sends s ON b.id = s.boulder_id AND s.angle = %(angle)s
            JOIN
                climbing.challenges c ON s.challenge_id = c.id
            JOIN
                climbing.users u ON s.user_id = u.id
        """,
        conn,
        params={"angle": angle},
    )

    grade_counts = pd.read_sql(
        """
            SELECT
                ROUND(average_grade) as grade,
                COUNT(id) as count
            FROM
                climbing.boulder_grades
            WHERE
                angle = %(angle)s
            GROUP BY
                ROUND(average_grade)
            ORDER BY
                ROUND(average_grade)
        """,
        conn,
        params={"angle": angle},
    )

    built_boulder_counts = pd.read_sql(
        """
            SELECT
                u.name as built_by,
                COUNT(b.id) as count
            FROM
                climbing.boulders b
            JOIN climbing.users u ON b.built_by = u.id
            GROUP BY
                u.name
        """,
        conn,
    )

    sandbag_and_soft = pd.read_sql(
        """
            WITH a AS (
                SELECT
                    s.user_id,
                    s.grade,
                    bg.average_grade
                FROM
                    climbing.sends s
                JOIN climbing.boulder_grades bg ON bg.id = s.boulder_id
            )
            SELECT
                u.name,
                count(CASE WHEN grade < average_grade-1 THEN 1 END) as sandbag_count,
                count(CASE WHEN grade > average_grade+1 THEN 1 END) as soft_count
            FROM
                a
            JOIN climbing.users u ON a.user_id = u.id
            GROUP BY
                name
            """,
        conn
    )

    sandbag_and_soft = dict(zip(sandbag_and_soft["name"], sandbag_and_soft[["sandbag_count", "soft_count"]].apply(lambda x: x.to_list(), axis=1)))
    grade_counts = dict(zip(grade_counts["grade"], grade_counts["count"]))
    built_boulder_counts = dict(zip(built_boulder_counts["built_by"], built_boulder_counts["count"]))
    # Fill in missing grades
    for i in range(0, 52):
        if i not in grade_counts:
            grade_counts[i] = 0

    all_climbing_stats = create_climbing_stats(df, grade_counts, built_boulder_counts, sandbag_and_soft)

    return json.dumps(all_climbing_stats)


@app.route('/climbing/app', methods=['GET'])
def climbing_app():
    versions = [
        {
            "version": "1.2.6",
            "name": "climbing_app_1.2.6.apk",
            "description": PATCH_126
        },
        {
            "version": "1.2.5",
            "name": "climbing_app_1.2.5.apk",
            "description": PATCH_125
        },
        {
            "version": "1.2.4",
            "name": "climbing_app_1.2.4.apk",
            "description": PATCH_124
        },
        {
            "version": "1.2.3",
            "name": "climbing_app_1.2.3.apk",
            "description": PATCH_123
        },
        {
            "version": "1.2.2",
            "name": "climbing_app_1.2.2.apk",
            "description": PATCH_122
        },
        {
            "version": "1.2.1",
            "name": "climbing_app_1.2.1.apk",
            "description": PATCH_121
        },
        {
            "version": "1.2.0",
            "name": "climbing_app_1.2.0.apk",
            "description": PATCH_120
        },
        {
            "version": "1.1.6",
            "name": "climbing_app_1.1.6.apk",
            "description": PATCH_116
        },
        {
            "version": "1.1.5",
            "name": "climbing_app_1.1.5.apk",
            "description": PATCH_115
        },
        {
            "version": "1.1.4",
            "name": "climbing_app_1.1.4.apk",
            "description": PATCH_114
        },
        {
            "version": "1.1.3",
            "name": "climbing_app_1.1.3.apk",
            "description": PATCH_113
        },
        {
            "version": "1.1.2",
            "name": "climbing_app_1.1.2.apk",
            "description": PATCH_112
        },
        {
            "version": "1.1.1",
            "name": "climbing_app_1.1.1.apk",
            "description": PATCH_111
        },
        {
            "version": "1.1.0",
            "name": "climbing_app_1.1.0.apk",
            "description": PATCH_110
        },
        {
            "version": "1.0.1",
            "name": "climbing_app_1.0.1.apk",
            "description": PATCH_101
        },
        {
            "version": "1.0.0",
            "name": "climbing_app_1.0.0.apk",
            "description": PATCH_100
        },
    ]

    return render_template("climbing_app.html", versions=versions)


@app.route('/climbing/set_description', methods=['POST'])
@token_required
def set_description(current_user):
    data = request.get_json()
    description = data["description"]

    if current_user["username"] == "Nepřihlášen":
        return "Musíte být přihlášen.", 400

    conn = psycopg2.connect(
        **db_conn
    )

    cur = conn.cursor()
    cur.execute(
        f"UPDATE climbing.users SET description = %(description)s WHERE name = %(username)s",
        {"description": description, "username": current_user["username"]}
    )

    conn.commit()
    cur.close()
    conn.close()

    return "OK", 200


@app.route('/climbing/set_border/<int:border_id>', methods=['GET'])
@token_required
def set_border(current_user, border_id):
    if current_user["username"] == "Nepřihlášen":
        return "Musíte být přihlášen.", 401

    conn = psycopg2.connect(
        **db_conn
    )

    cur = conn.cursor()
    cur.execute(
        f"UPDATE climbing.users SET border = %(border_id)s WHERE name = %(username)s",
        {"border_id": border_id, "username": current_user["username"]}
    )

    conn.commit()
    cur.close()
    conn.close()

    return "OK", 200


@app.route('/climbing/get_tags', methods=['GET'])
def get_tags():
    conn = psycopg2.connect(
        **db_conn
    )

    df = pd.read_sql(
        f"SELECT id, name FROM climbing.tags",
        conn,
    )

    return df.to_json(orient="records")


@app.route('/climbing/get_config', methods=['GET'])
def get_angle():
    conn = psycopg2.connect(
        **db_conn
    )

    df = pd.read_sql(
        f"SELECT key, value FROM climbing.config",
        conn,
    )

    key_value = df.set_index("key").to_dict()["value"]
    # Convert angle to int
    key_value["angle"] = int(key_value["angle"])

    return key_value


@app.route('/climbing/set_angle/<int:angle>', methods=['GET'])
@token_required
def set_angle(current_user, angle):
    if current_user["username"] == "Nepřihlášen":
        return "Musíte být přihlášen.", 401

    if not current_user["admin"]:
        return "Nemáte oprávnění.", 403

    conn = psycopg2.connect(
        **db_conn
    )

    cur = conn.cursor()
    cur.execute(
        f"UPDATE climbing.config SET value = %(angle)s WHERE key = 'angle'",
        {"angle": angle}
    )

    conn.commit()
    cur.close()
    conn.close()

    return "OK", 200


@app.route('/climbing/crack/log_send', methods=['POST'])
@token_required
def climbing_crack_log_send(current_user):
    if current_user["username"] == "Nepřihlášen":
        return "Musíte být přihlášen.", 401

    data = request.get_json()
    is_vertical = data["is_vertical"]
    crack_type = data["crack_type"]
    whole_times = data["whole_times"]
    decimal_times = data["decimal_times"]

    if is_vertical is None or crack_type is None or whole_times is None or decimal_times is None:
        return "Něco chybí.", 400

    climbed_times = whole_times + decimal_times/10

    conn = psycopg2.connect(
        **db_conn
    )

    # Insert send into db
    cur = conn.cursor()
    cur.execute(
        f"""
        INSERT INTO climbing.crack_sends (user_id, is_vertical, crack_type, climbed_times, sent_date)
        VALUES
            (
                (SELECT id FROM climbing.users WHERE name = %(username)s),
                %(is_vertical)s,
                %(crack_type)s,
                %(climbed_times)s,
                NOW()
            )
        """,
        {"username": current_user["username"], "is_vertical": is_vertical, "crack_type": crack_type, "climbed_times": climbed_times}
    )

    conn.commit()
    cur.close()
    conn.close()

    return "OK", 200


@app.route('/climbing/crack/stats', methods=['GET'])
def climbing_crack_stats():

    conn = psycopg2.connect(
        **db_conn
    )

    df = pd.read_sql(
        """
            SELECT
                is_vertical,
                crack_type,
                climbed_times,
                sent_date,
                u.name as username
            FROM
                climbing.crack_sends s
            JOIN
                climbing.users u ON s.user_id = u.id
        """,
        conn,
    )

    all_crack_stats = create_crack_climbing_stats(df)

    return json.dumps(all_crack_stats)


@app.route('/climbing/sends/<string:date>', methods=['GET'])
def climbing_sends(date):
    conn = psycopg2.connect(
        **db_conn
    )

    df = pd.read_sql(
        f"""
            SELECT
                s.id,
                b.name,
                ROUND(bg.average_grade) as grade,
                s.attempts,
                s.rating,
                s.sent_date,
                u.name as username,
                s.challenge_id
            FROM
                climbing.sends s
            JOIN
                climbing.boulders b ON s.boulder_id = b.id
            JOIN
                climbing.boulder_grades bg ON s.boulder_id = bg.id
            JOIN
                climbing.users u ON s.user_id = u.id
            WHERE
                (sent_date AT TIME ZONE 'UTC' AT TIME ZONE 'Europe/Prague')::date = %(date)s
            ORDER BY
                s.sent_date DESC
        """,
        conn,
        params={"date": date},
    )

    return df.to_json(orient="records")
