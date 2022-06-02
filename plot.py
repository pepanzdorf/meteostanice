import plotly.graph_objects as go
from plotly.subplots import make_subplots


def create_plot_main(df, plot_name):
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        specs=[[{"secondary_y": True}], [{"secondary_y": True}], [{"secondary_y": True}]],
    )

    fig.add_trace(
        go.Scatter(
            x=df["inserted_at"],
            y=df["lux"],
            mode="lines",
            name="Intenzita světla",
            hovertemplate="%{y}lux<br>%{x}",
            line_color="Gold",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df["inserted_at"],
            y=df["temperature"],
            mode="lines",
            name="Teplota (meteostanice)",
            hovertemplate="%{y}°C<br>%{x}",
            line_color="Red",
        ),
        row=1,
        col=1,
        secondary_y=True,
    )

    fig.add_trace(
        go.Scatter(
            x=df["inserted_at"],
            y=df["temperature2"],
            mode="lines",
            name="Teplota (balkon)",
            hovertemplate="%{y}°C<br>%{x}",
            line_color="#fc00c6",
        ),
        row=1,
        col=1,
        secondary_y=True,
    )

    fig.add_trace(
        go.Scatter(
            x=df["inserted_at"],
            y=(df["pressure"] / 100).round(2),
            mode="lines",
            name="Tlak",
            hovertemplate="%{y}hPa<br>%{x}",
            line_color="Green",
        ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df["inserted_at"],
            y=df["rain"]*0.08,
            mode="lines",
            name="Srážky",
            hovertemplate="%{y}mm/5min<br>%{x}",
            line_shape="vh",
            fill="tozeroy",
            fillcolor="Blue",
            line_color="Blue",
        ),
        row=2,
        col=1,
        secondary_y=True,
    )

    fig.add_trace(
        go.Scatter(
            x=df["inserted_at"],
            y=df["solar"]/(4095/3.4),
            mode="lines",
            name="Osvícení (solární panel)",
            hovertemplate="%{y}V<br>%{x}",
            line_color="#f2d324",
        ),
        row=3,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df["inserted_at"],
            y=df["light"],
            mode="lines",
            name="Osvícení",
            hovertemplate="%{y}%<br>%{x}",
            line_color="#d9bf2b",
        ),
        row=3,
        col=1,
        secondary_y=True,
    )

    fig.add_trace(
        go.Scatter(
            x=df["inserted_at"],
            y=df["humidity"],
            mode="lines",
            name="Vlhkost",
            hovertemplate="%{y}%<br>%{x}",
            line_color="Brown",
        ),
        row=3,
        col=1,
        secondary_y=True,
    )

    fig.update_layout(
        legend=dict({"bgcolor": "rgba(0, 0, 0, 0)"}),
        paper_bgcolor="rgba(0,0,0,0)",
        modebar=dict(
            {
                "bgcolor": "rgb(0,0,0,0)",
                "color": "rgb(150,150,150)",
                "activecolor": "rgb(100,100,100)",
            }
        ),
        title=dict({"text": "Počasí celkově"}),
        title_font_family="Arial",
        title_font_size=40,
        title_xanchor="center",
        title_x=0.5,
        font=dict(color="black"),
        margin=dict({"t": 60, "b": 0, "r": 0, "l": 0}),
        shapes=[
            dict(
                type="rect",
                xref="x domain",
                yref="y2",
                x0=0,
                y0=0,
                x1=1,
                y1=min(df["temperature"].min() - 1, df["temperature2"].min() - 1, -1),
                fillcolor="lightblue",
                opacity=0.5,
                layer="below",
                line_width=0,
            )
        ],
        xaxis_showticklabels=True,
        xaxis2_showticklabels=True,
        xaxis3_showticklabels=True,
    )

    fig.update_xaxes(title_text="Datum", row=3)
    fig.update_yaxes(title_text="Intenzita světla (lux)", secondary_y=False, hoverformat='.2f', row=1)
    fig.update_yaxes(title_text="Teplota (°C)", secondary_y=True, hoverformat='.2f', row=1)
    fig.update_yaxes(title_text="Tlak (hPa)", secondary_y=False, hoverformat='.2f', row=2)
    fig.update_yaxes(title_text="Srážky (mm/5min)", secondary_y=True, row=2)
    fig.update_yaxes(title_text="Osvícení solární panel (V)", secondary_y=False, hoverformat='.2f', row=3)
    fig.update_yaxes(title_text="Vlhkost vzduchu / osvícení (%)", secondary_y=True, row=3)

    config = {
        "displayModeBar": True,
        "displaylogo": False,
        "toImageButtonOptions": {
            "format": "png",
            "filename": "downloaded_plot",
            "height": 1500,
            "width": 1500,
        },
    }

    plot = fig.to_html(config=config)[56:-16]
    plot = plot[:4] + f' id="{plot_name}"' + plot[4:]
    return plot


def create_plot_rain(df, plot_name):
    fig = make_subplots(
        rows=1,
        cols=1,
        shared_xaxes=True,
        specs=[[{}]],
    )

    fig.add_trace(
        go.Scatter(
            x=df["inserted_at"],
            y=df["rain"]*0.08,
            mode="lines",
            name="Srážky",
            hovertemplate="%{y}mm/5min<br>%{x}",
            line_shape="vh",
            fill="tozeroy",
            fillcolor="Blue",
            line_color="Blue",
        ),
        row=1,
        col=1,
    )

    fig.update_layout(
        legend=dict({"bgcolor": "rgba(0, 0, 0, 0)"}),
        paper_bgcolor="rgba(0,0,0,0)",
        modebar=dict(
            {
                "bgcolor": "rgb(0,0,0,0)",
                "color": "rgb(150,150,150)",
                "activecolor": "rgb(100,100,100)",
            }
        ),
        title=dict({"text": "Srážky"}),
        title_font_family="Arial",
        title_font_size=40,
        title_xanchor="center",
        title_x=0.5,
        font=dict(color="black"),
        margin=dict({"t": 60, "b": 0, "r": 0, "l": 0}),
    )

    fig.update_xaxes(title_text="Datum")
    fig.update_yaxes(title_text="Srážky (mm/5min)")

    config = {
        "displayModeBar": True,
        "displaylogo": False,
        "toImageButtonOptions": {
            "format": "png",
            "filename": "downloaded_plot",
            "height": 500,
            "width": 1500,
        },
    }

    plot = fig.to_html(config=config)[56:-16]
    plot = plot[:4] + f' id="{plot_name}"' + plot[4:]
    return plot


def create_plot_press(df, plot_name):
    fig = make_subplots(
        rows=1,
        cols=1,
        shared_xaxes=True,
        specs=[
            [{}],
        ],
    )

    fig.add_trace(
        go.Scatter(
            x=df["inserted_at"],
            y=(df["pressure"] / 100).round(2),
            mode="lines",
            name="Tlak",
            hovertemplate="%{y}hPa<br>%{x}",
            line_color="Green",
        ),
        row=1,
        col=1,
    )

    fig.update_layout(
        legend=dict({"bgcolor": "rgba(0, 0, 0, 0)"}),
        paper_bgcolor="rgba(0,0,0,0)",
        modebar=dict(
            {
                "bgcolor": "rgb(0,0,0,0)",
                "color": "rgb(150,150,150)",
                "activecolor": "rgb(100,100,100)",
            }
        ),
        title=dict({"text": "Tlak"}),
        title_font_family="Arial",
        title_font_size=40,
        title_xanchor="center",
        title_x=0.5,
        margin=dict({"t": 60, "b": 0, "r": 0, "l": 0}),
        font=dict(color="black"),
    )

    fig.update_xaxes(title_text="Datum")
    fig.update_yaxes(title_text="Tlak (hPa)", hoverformat='.2f')

    config = {
        "displayModeBar": True,
        "displaylogo": False,
        "toImageButtonOptions": {
            "format": "png",
            "filename": "downloaded_plot",
            "height": 500,
            "width": 1500,
        },
    }

    plot = fig.to_html(config=config)[56:-16]
    plot = plot[:4] + f' id="{plot_name}"' + plot[4:]
    return plot


def create_plot_temp(df, plot_name):
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        specs=[[{"secondary_y": True}], [{"secondary_y": True}]],
        row_heights=[500, 500],
    )

    fig.add_trace(
        go.Scatter(
            x=df["inserted_at"],
            y=df["lux"],
            mode="lines",
            name="Intenzita světla",
            hovertemplate="%{y}lux<br>%{x}",
            line_color="Gold",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df["inserted_at"],
            y=df["temperature"],
            mode="lines",
            name="Teplota",
            hovertemplate="%{y}°C<br>%{x}",
            line_color="Red",
        ),
        row=1,
        col=1,
        secondary_y=True,
    )

    fig.add_trace(
        go.Scatter(
            x=df["inserted_at"],
            y=df["temperature2"],
            mode="lines",
            name="Teplota (balkon)",
            hovertemplate="%{y}°C<br>%{x}",
            line_color="#fc00c6",
        ),
        row=1,
        col=1,
        secondary_y=True,
    )

    fig.add_trace(
        go.Scatter(
            x=df["inserted_at"],
            y=df["solar"]/(4095/3.4),
            mode="lines",
            name="Osvícení (solární panel)",
            hovertemplate="%{y}V<br>%{x}",
            line_color="#f2d324",
        ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df["inserted_at"],
            y=df["light"],
            mode="lines",
            name="Osvícení",
            hovertemplate="%{y}%<br>%{x}",
            line_color="#d9bf2b",
        ),
        row=2,
        col=1,
        secondary_y=True,
    )

    fig.update_layout(
        legend=dict({"bgcolor": "rgba(0, 0, 0, 0)"}),
        paper_bgcolor="rgba(0,0,0,0)",
        modebar=dict(
            {
                "bgcolor": "rgb(0,0,0,0)",
                "color": "rgb(150,150,150)",
                "activecolor": "rgb(100,100,100)",
            }
        ),
        title=dict({"text": "Teplota"}),
        title_font_family="Arial",
        title_font_size=40,
        title_xanchor="center",
        title_x=0.5,
        font=dict(color="black"),
        margin=dict({"t": 60, "b": 0, "r": 0, "l": 0}),
        shapes=[
            dict(
                type="rect",
                xref="x domain",
                yref="y2",
                x0=0,
                y0=0,
                x1=1,
                y1=min(df["temperature"].min() - 1, df["temperature2"].min() - 1, -1),
                fillcolor="lightblue",
                opacity=0.5,
                layer="below",
                line_width=0,
            )
        ],
        xaxis_showticklabels=True,
        xaxis2_showticklabels=True,
    )

    fig.update_xaxes(title_text="Datum", row=2)
    fig.update_yaxes(title_text="Teplota (°C)", secondary_y=True, hoverformat='.2f', row=1)
    fig.update_yaxes(title_text="Intenzita světla (lux)", secondary_y=False, hoverformat='.2f', row=1)
    fig.update_yaxes(title_text="Osvícení (%)", secondary_y=True, row=2)
    fig.update_yaxes(title_text="Osvícení solární panel (V)", secondary_y=False, hoverformat='.2f', row=2)

    config = {
        "displayModeBar": True,
        "displaylogo": False,
        "toImageButtonOptions": {
            "format": "png",
            "filename": "downloaded_plot",
            "height": 1000,
            "width": 1500,
        },
    }

    plot = fig.to_html(config=config, full_html=False)
    plot = plot[:4] + f' id="{plot_name}"' + plot[4:]
    return plot


def create_plot_humi(df, plot_name):
    fig = make_subplots(
        rows=1,
        cols=1,
        shared_xaxes=True,
        specs=[
            [{}],
        ],
    )

    fig.add_trace(
        go.Scatter(
            x=df["inserted_at"],
            y=df["humidity"],
            mode="lines",
            name="Relativní vlhkost vzduchu",
            hovertemplate="%{y}%<br>%{x}",
            line_color="Brown",
        ),
        row=1,
        col=1,
    )

    fig.update_layout(
        legend=dict({"bgcolor": "rgba(0, 0, 0, 0)"}),
        paper_bgcolor="rgba(0,0,0,0)",
        modebar=dict(
            {
                "bgcolor": "rgb(0,0,0,0)",
                "color": "rgb(150,150,150)",
                "activecolor": "rgb(100,100,100)",
            }
        ),
        title=dict({"text": "Vlhkost"}),
        title_font_family="Arial",
        title_font_size=40,
        title_xanchor="center",
        title_x=0.5,
        margin=dict({"t": 60, "b": 0, "r": 0, "l": 0}),
        font=dict(color="black"),
    )

    fig.update_xaxes(title_text="Datum")
    fig.update_yaxes(title_text="Relativní vlhkost vzduchu (%)")

    config = {
        "displayModeBar": True,
        "displaylogo": False,
        "toImageButtonOptions": {
            "format": "png",
            "filename": "downloaded_plot",
            "height": 500,
            "width": 1500,
        },
    }

    plot = fig.to_html(config=config)[56:-16]
    plot = plot[:4] + f' id="{plot_name}"' + plot[4:]
    return plot


def create_table(data, table_name, unit):
    for i in range(0, len(data)):
        try:
            data[i] = data[i].round(2)
        except (ValueError, AttributeError):
            pass

    fig = make_subplots(
        rows=1,
        cols=1,
        specs=[[{"type": "table"}]],
    )

    fig.add_trace(
        go.Table(
            header=dict(
                values=[
                    unit,
                    "Za posledních 24 hodin",
                    "Za poslední týden",
                    "Za poslednch 30 dní",
                    "Historicky",
                ],
                line_color="black",
                fill_color="rgb(210, 210, 210)",
                align="center",
                height=50,
            ),
            cells=dict(
                values=[
                    ["Maximum", "Minimum"],
                    [data[0], data[1]],
                    [data[2], data[3]],
                    [data[4], data[5]],
                    [data[6], data[7]],
                ],
                line_color="black",
                fill=dict(color=["rgb(210, 210, 210)", "rgb(225, 225, 225)"]),
                align=["center", "left"],
                height=35,
            ),
        ),
        row=1,
        col=1,
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict({"t": 5, "b": 5, "r": 5, "l": 5}),
    )

    config = {"displayModeBar": False}

    plot = fig.to_html(config=config)[56:-16]
    plot = plot[:4] + f' id="{table_name}"' + plot[4:]
    return plot


def create_table_main(value, table_name):
    fig = make_subplots(
        rows=1,
        cols=1,
        specs=[[{"type": "table"}]],
    )

    fig.add_trace(
        go.Table(
            columnwidth=[60, 80],
            header=dict(
                values=[
                    value[0].strftime("%Y-%m-%d %H:%M"),
                    "Teplota(°C)",
                    "Teplota-balkon(°C)",
                    "Tlak(hPa)",
                ],
                line_color="black",
                fill_color="rgb(210, 210, 210)",
                align="center",
                height=35,
            ),
            cells=dict(
                values=[
                    ["Aktuálně", "", ""],
                    [value[1], "Srážky(mm/5min)", value[4]],
                    [value[2], "Relativní vlhkost vzduchu(%)", value[5]],
                    [value[3], "Intenzita světla (lux)", value[6]],
                ],
                line_color="black",
                fill=dict(color=[["rgb(210, 210, 210)"], ["rgb(225, 225, 225)", "rgb(210, 210, 210)"]*2]),
                align="center",
                height=35,
            ),
        ),
        row=1,
        col=1,
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict({"t": 60, "b": 5, "r": 5, "l": 5}),
    )

    config = {"displayModeBar": False}

    plot = fig.to_html(config=config)[56:-16]
    plot = plot[:4] + f' id="{table_name}"' + plot[4:]
    return plot


def create_table_recent(value, table_name):
    fig = make_subplots(
        rows=1,
        cols=1,
        specs=[[{"type": "table"}]],
    )
    fig.add_trace(
        go.Table(
            columnwidth=[60, 60],
            header=dict(
                values=[
                    f"{value[0]}<br>{value[2].strftime('%Y-%m-%d %H:%M')}",
                    value[1],
                ],
                line_color="black",
                fill_color=["rgb(210, 210, 210)", "rgb(225, 225, 225)"],
                align="center",
                height=35,
            ),
        ),
        row=1,
        col=1,
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict({"t": 5, "b": 5, "r": 5, "l": 5}),
    )

    config = {"displayModeBar": False}

    plot = fig.to_html(config=config)[56:-16]
    plot = plot[:4] + f' id="{table_name}"' + plot[4:]
    return plot
