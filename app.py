from flask import Flask, render_template, abort, redirect, request
from plot import *
import pandas as pd
from datetime import datetime, timedelta
import psycopg2
from environment import DB_PASS
from pytz import timezone


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
        "SELECT * FROM test.records WHERE inserted_at BETWEEN %(start)s AND %(end)s",
        conn,
        params={"start": start, "end": end},
    )
    if not df.empty:
        df["inserted_at"] = (
            df["inserted_at"].dt.tz_localize("utc").dt.tz_convert("Europe/Prague")
        )
        df = df.sort_values(by=["inserted_at"], axis=0, ascending=True)
    return df


def select_last_record():
    conn = psycopg2.connect(
        database="postgres",
        user="postgres",
        password=DB_PASS,
        host="89.221.216.28",
    )
    df_last_record = pd.read_sql(
        "SELECT * FROM test.records WHERE inserted_at=(SELECT max(inserted_at) FROM test.records);",
        conn,
    )
    df_last_record["inserted_at"] = (
        df_last_record["inserted_at"]
        .dt.tz_localize("utc")
        .dt.tz_convert("Europe/Prague")
    )
    return df_last_record


def create_list(df, df_day, df_week, df_month, value):
    if value == "pressure":
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
                return datetime.utcnow() - timedelta(days=30), datetime.utcnow()
            try:
                start_date = datetime.strptime(start_date, "%Y-%m-%dT%H:%M").replace(
                    tzinfo=timezone("Europe/Prague")
                )
                end_date = datetime.strptime(end_date, "%Y-%m-%dT%H:%M").replace(
                    tzinfo=timezone("Europe/Prague")
                )
                return start_date, end_date
            except ValueError:
                return (
                    datetime.utcnow() - timedelta(days=30),
                    datetime.utcnow(),
                )
        else:
            try:
                start_date = datetime.strptime(
                    f"{start_date}T00:00", "%Y-%m-%dT%H:%M"
                ).replace(tzinfo=timezone("Europe/Prague"))
                end_date = datetime.strptime(
                    f"{end_date}T23:59", "%Y-%m-%dT%H:%M"
                ).replace(tzinfo=timezone("Europe/Prague"))
                return start_date, end_date
            except ValueError:
                return datetime.utcnow() - timedelta(days=30), datetime.utcnow()
    else:
        return datetime.utcnow() - timedelta(days=30), datetime.utcnow()


HOME = read_content("home")
INFO = read_content("info")
RAIN = read_content("rain")


@app.route("/")
def index():
    return redirect("/home")


@app.route("/home")
def home():
    start_date, end_date = input_to_datetime(
        request.args.get("start-date"),
        request.args.get("start-time"),
        request.args.get("end-date"),
        request.args.get("end-time"),
    )
    df = select_timedelta(start_date, end_date)
    df_last_record = select_last_record()
    return render_template(
        "template.html",
        title="Home",
        content=HOME,
        plot=create_plot_main(df, "main-plot"),
        form=render_template(
            "form.html",
            today_date=f"'{datetime.now(timezone('Europe/Prague')).strftime('%Y-%m-%d')}'",
        ),
        table=create_table_main(
            (
                df_last_record["temperature"].round(2),
                (df_last_record["pressure"] / 100).round(2),
                df_last_record["rain"] * 0.08,
                df_last_record["inserted_at"].max(),
            ),
            "recent-main",
        ),
    )


@app.route("/rain")
def rain():
    start_date, end_date = input_to_datetime(
        request.args.get("start-date"),
        request.args.get("start-time"),
        request.args.get("end-date"),
        request.args.get("end-time"),
    )
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
    return render_template(
        "template.html",
        content=RAIN,
        title="Srážky",
        plot=create_plot_rain(df, "rain-plot"),
        table=create_table(
            create_list(df_all_time, df_day, df_week, df_month, "rain"),
            "rain-table",
            "mm/5min",
        ),
        form=render_template(
            "form.html",
            today_date=f"'{datetime.now(timezone('Europe/Prague')).strftime('%Y-%m-%d')}'",
        ),
        table_recent=create_table_recent(
            (
                "Aktuálně(mm/5min)",
                df_last_record["rain"] * 0.08,
                df_last_record["inserted_at"].max(),
            ),
            "recent-rain",
        ),
    )


@app.route("/press")
def press():
    start_date, end_date = input_to_datetime(
        request.args.get("start-date"),
        request.args.get("start-time"),
        request.args.get("end-date"),
        request.args.get("end-time"),
    )
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
    return render_template(
        "template.html",
        title="Tlak",
        plot=create_plot_press(df, "press-plot"),
        table=create_table(
            create_list(df_all_time, df_day, df_week, df_month, "pressure"),
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
                (df_last_record["pressure"] / 100).round(2),
                df_last_record["inserted_at"].max(),
            ),
            "recent-press",
        ),
    )


@app.route("/temp")
def temp():
    start_date, end_date = input_to_datetime(
        request.args.get("start-date"),
        request.args.get("start-time"),
        request.args.get("end-date"),
        request.args.get("end-time"),
    )
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
    return render_template(
        "template.html",
        title="Teplota",
        plot=create_plot_temp(df, "temp-plot"),
        table=create_table(
            create_list(df_all_time, df_day, df_week, df_month, "temperature"),
            "temp-table",
            "°C",
        ),
        form=render_template(
            "form.html",
            today_date=f"'{datetime.now(timezone('Europe/Prague')).strftime('%Y-%m-%d')}'",
        ),
        table_recent=create_table_recent(
            (
                "Aktuálně(°C)",
                df_last_record["temperature"].round(2),
                df_last_record["inserted_at"].max(),
            ),
            "recent-temp",
        ),
    )


@app.route("/info")
def info():
    return render_template(
        "template.html",
        content=INFO,
        title="Info",
        table="<img src='/static/srazkomer.png' style='width:384px;height:216px;float: right;'>",
    )


@app.route("/api/v1/weather")
def weather():
    df = select_timedelta((datetime.utcnow() - timedelta(hours=1)), datetime.utcnow())
    df['inserted_at'] = df['inserted_at'].apply(lambda x: x.value/1000)
    df = df.reset_index().to_dict(orient='list')
    return df


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
