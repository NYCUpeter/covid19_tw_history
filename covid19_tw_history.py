import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output, State
import dash

# 讀取資料與前處理
df = pd.read_csv("Day_Confirmation_Age_County_Gender_19CoV.csv", encoding='utf-8')
df["個案研判日"] = pd.to_datetime(df["個案研判日"])
df_local = df[df["是否為境外移入"] == 0].copy()
target_counties = [
    "基隆市", "台北市", "新北市", "桃園市", "新竹市", "新竹縣",
    "苗栗縣", "台中市", "彰化縣", "南投縣", "雲林縣", "嘉義市",
    "嘉義縣", "台南市", "高雄市", "屏東縣", "台東縣", "花蓮縣",
    "宜蘭縣", "澎湖縣", "金門縣", "連江縣"
]
df_local = df_local[df_local["縣市"].isin(target_counties)]
daily_county = df_local.groupby(["個案研判日", "縣市"])["確定病例數"].sum().reset_index()

min_date = daily_county["個案研判日"].min()
max_date = daily_county["個案研判日"].max()

app = Dash(__name__)

app.layout = html.Div([
    html.H3("台灣目標縣市確診數趨勢", style={"font-family": "Microsoft JhengHei"}),

    # 四個單選縣市下拉選單
    html.Div([
        html.Div([
            html.Label("選擇縣市1："),
            dcc.Dropdown(
                id='county-dropdown-1',
                options=[{"label": c, "value": c} for c in target_counties],
                value=target_counties[0],  # 預設第一個縣市
                clearable=True,
                style={"width": "200px"}
            ),
        ]),
        html.Div([
            html.Label("選擇縣市2："),
            dcc.Dropdown(
                id='county-dropdown-2',
                options=[{"label": c, "value": c} for c in target_counties],
                value=None,
                clearable=True,
                style={"width": "200px"}
            ),
        ]),
        html.Div([
            html.Label("選擇縣市3："),
            dcc.Dropdown(
                id='county-dropdown-3',
                options=[{"label": c, "value": c} for c in target_counties],
                value=None,
                clearable=True,
                style={"width": "200px"}
            ),
        ]),
        html.Div([
            html.Label("選擇縣市4："),
            dcc.Dropdown(
                id='county-dropdown-4',
                options=[{"label": c, "value": c} for c in target_counties],
                value=None,
                clearable=True,
                style={"width": "200px"}
            ),
        ]),
    ], style={"margin-bottom": "20px", "display": "flex", "gap": "20px"}),

    html.Div([
        html.Label("起始日期（YYYY-MM-DD）:"),
        dcc.Input(id='start-date-input', type='text', value=str(min_date.date())),
        html.Label("結束日期（YYYY-MM-DD）:"),
        dcc.Input(id='end-date-input', type='text', value=str(max_date.date())),
        html.Button("更新圖表", id='update-button', n_clicks=0),
    ], style={"margin-bottom": "20px", "display": "flex", "gap": "10px"}),

    html.Div(id="date-range-text", style={"margin-bottom": "10px", "font-weight": "bold"}),

    dcc.Graph(id='graph-daily'),
    html.Button("下載每日確診圖 (PNG)", id="download-daily-btn"),
    dcc.Download(id="download-daily"),

    dcc.Graph(id='graph-cumulative'),
    html.Button("下載累積確診圖 (PNG)", id="download-cum-btn"),
    dcc.Download(id="download-cum"),
])


@app.callback(
    Output('graph-daily', 'figure'),
    Output('graph-cumulative', 'figure'),
    Output('date-range-text', 'children'),
    Output('start-date-input', 'value'),
    Output('end-date-input', 'value'),
    Input('update-button', 'n_clicks'),
    Input('graph-daily', 'relayoutData'),
    Input('graph-cumulative', 'relayoutData'),
    Input('county-dropdown-1', 'value'),
    Input('county-dropdown-2', 'value'),
    Input('county-dropdown-3', 'value'),
    Input('county-dropdown-4', 'value'),
    State('start-date-input', 'value'),
    State('end-date-input', 'value'),
)
def update_all(n_clicks, relayout_daily, relayout_cum,
               c1, c2, c3, c4,
               start_input, end_input):
    triggered = dash.callback_context.triggered
    triggered_id = triggered[0]['prop_id'].split('.')[0] if triggered else None

    start, end = None, None

    # 先嘗試從輸入框讀日期（手動按按鈕或首次載入）
    try:
        start = pd.to_datetime(start_input)
        end = pd.to_datetime(end_input)
    except Exception:
        start = min_date
        end = max_date

    # 若是圖表縮放觸發，改用縮放的日期範圍
    if triggered_id in ['graph-daily', 'graph-cumulative']:
        relayout_data = relayout_daily if triggered_id == 'graph-daily' else relayout_cum
        if relayout_data:
            try:
                if 'xaxis.range[0]' in relayout_data and 'xaxis.range[1]' in relayout_data:
                    start = pd.to_datetime(relayout_data['xaxis.range[0]'])
                    end = pd.to_datetime(relayout_data['xaxis.range[1]'])
                elif 'xaxis.range' in relayout_data and isinstance(relayout_data['xaxis.range'], list):
                    start = pd.to_datetime(relayout_data['xaxis.range'][0])
                    end = pd.to_datetime(relayout_data['xaxis.range'][1])
            except Exception:
                pass

    # 日期邊界檢查
    if start is None or end is None or start > end:
        start, end = min_date, max_date

    # 合併四個下拉選擇縣市，過濾 None 且去重複
    selected_counties = list({c for c in [c1, c2, c3, c4] if c})

    # 篩選資料
    if not selected_counties:
        # 沒選就空資料
        df_filtered = daily_county.iloc[0:0].copy()
    else:
        mask = (
            (daily_county["個案研判日"] >= start) &
            (daily_county["個案研判日"] <= end) &
            (daily_county["縣市"].isin(selected_counties))
        )
        df_filtered = daily_county.loc[mask].copy()

    # 計算累積確診數
    df_filtered["累積確診數"] = df_filtered.groupby("縣市")["確定病例數"].cumsum()

    # 畫每日確診數
    fig_daily = px.line(
        df_filtered,
        x="個案研判日",
        y="確定病例數",
        color="縣市",
        title="台灣目標縣市每日本土確診數"
    )
    fig_daily.update_layout(
        font=dict(family="Microsoft JhengHei", size=14),
        xaxis_title="日期",
        yaxis_title="每日確診數",
        xaxis=dict(
            rangeselector=dict(
                buttons=[
                    dict(count=7, label="1週", step="day", stepmode="backward"),
                    dict(count=1, label="1月", step="month", stepmode="backward"),
                    dict(step="all", label="全部")
                ]
            ),
            rangeslider=dict(visible=True),
            type="date"
        )
    )

    # 畫累積確診數
    fig_cum = px.line(
        df_filtered,
        x="個案研判日",
        y="累積確診數",
        color="縣市",
        title="台灣目標縣市累積本土確診數"
    )
    fig_cum.update_layout(
        font=dict(family="Microsoft JhengHei", size=14),
        xaxis_title="日期",
        yaxis_title="累積確診數",
        xaxis=dict(
            rangeselector=dict(
                buttons=[
                    dict(count=7, label="1週", step="day", stepmode="backward"),
                    dict(count=1, label="1月", step="month", stepmode="backward"),
                    dict(step="all", label="全部")
                ]
            ),
            rangeslider=dict(visible=True),
            type="date"
        )
    )

    display_text = f"📅 顯示中：{start.date()} 到 {end.date()}"
    return fig_daily, fig_cum, display_text, str(start.date()), str(end.date())


# 下載每日確診圖 PNG
@app.callback(
    Output("download-daily", "data"),
    Input("download-daily-btn", "n_clicks"),
    State("graph-daily", "figure"),
    prevent_initial_call=True
)
def download_daily_png(n_clicks, figure):
    if figure is None:
        return dash.no_update
    import plotly.io as pio
    img_bytes = pio.to_image(figure, format="png")
    return dcc.send_bytes(img_bytes, "daily_confirmed_cases.png")


# 下載累積確診圖 PNG
@app.callback(
    Output("download-cum", "data"),
    Input("download-cum-btn", "n_clicks"),
    State("graph-cumulative", "figure"),
    prevent_initial_call=True
)
def download_cum_png(n_clicks, figure):
    if figure is None:
        return dash.no_update
    import plotly.io as pio
    img_bytes = pio.to_image(figure, format="png")
    return dcc.send_bytes(img_bytes, "cumulative_confirmed_cases.png")


if __name__ == '__main__':
    app.run(debug=True)
