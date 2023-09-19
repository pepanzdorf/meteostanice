from flask import Flask, render_template, redirect, request
from plot import *
import pandas as pd
from datetime import datetime, timedelta
import psycopg2
from environment import DB_PASS
from pytz import timezone
import numpy as np
import json


app = Flask(__name__)


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
    df["inserted_at"] = df["inserted_at"].apply(lambda x: x.value / 1000000)
    df = df.where(pd.notnull(df), None)
    df = df.reset_index().to_dict(orient="list")
    return df


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
