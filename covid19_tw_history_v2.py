import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output, State
import dash
import plotly.io as pio

# 輔助函數：移除不合法屬性避免下載時錯誤
def sanitize_figure(fig):
    layout = fig.get('layout', {})
    xaxis = layout.get('xaxis', {})
    if '_template' in xaxis:
        xaxis.pop('_template')
    if 'rangeslider' in xaxis:
        rangeslider = xaxis['rangeslider']
        if 'yaxis' in rangeslider:
            rangeslider.pop('yaxis')
    return fig

# 讀取資料與前處理
df = pd.read_csv("Day_Confirmation_Age_County_Gender_19CoV.csv", encoding='utf-8')
df["個案研判日"] = pd.to_datetime(df["個案研判日"])
df_local = df[df["是否為境外移入"] == 0].copy()

# 高雄舊市區定義
old_kaohsiung_label = "舊高雄市"
old_kaohsiung_districts = [
    "鹽埕區", "鼓山區", "左營區", "楠梓區", "三民區",
    "新興區", "前金區", "苓雅區", "前鎮區", "旗津區", "小港區"
]

# 縣市清單（不含高雄市，因為會另外放高雄市與舊高雄市）
target_counties = [
    "基隆市", "台北市", "新北市", "桃園市", "新竹市", "新竹縣",
    "苗栗縣", "台中市", "彰化縣", "南投縣", "雲林縣", "嘉義市",
    "嘉義縣", "台南市", "屏東縣", "台東縣", "花蓮縣",
    "宜蘭縣", "澎湖縣", "金門縣", "連江縣"
]

# 下拉選單選項（含高雄市與舊高雄市）
dropdown_options = [{"label": c, "value": c} for c in target_counties] + [
    {"label": "高雄市", "value": "高雄市"},
    {"label": old_kaohsiung_label, "value": old_kaohsiung_label},
]

# 篩選本土病例中縣市為目標縣市或高雄市
df_local = df_local[
    (df_local["縣市"].isin(target_counties)) |
    (df_local["縣市"] == "高雄市")
].copy()

# 標示「舊高雄市」區域
df_local["縣市_顯示"] = df_local["縣市"]
df_local.loc[
    (df_local["縣市"] == "高雄市") & (df_local["鄉鎮"].isin(old_kaohsiung_districts)),
    "縣市_顯示"
] = old_kaohsiung_label

# 計算舊高雄市 11 區資料
daily_old = df_local[df_local["縣市_顯示"] == old_kaohsiung_label].groupby(
    ["個案研判日", "縣市_顯示"])["確定病例數"].sum().reset_index()

# 計算高雄市全區資料（包含11區和其他區）
daily_kao = df_local[df_local["縣市"] == "高雄市"].groupby(
    ["個案研判日"])["確定病例數"].sum().reset_index()
daily_kao["縣市_顯示"] = "高雄市"

# 計算其他縣市（排除高雄市與舊高雄市）
other_daily = df_local[
    (df_local["縣市"] != "高雄市") & (df_local["縣市_顯示"] != old_kaohsiung_label)
].groupby(["個案研判日", "縣市_顯示"])["確定病例數"].sum().reset_index()

# 合併所有縣市資料
daily_county = pd.concat([daily_kao, daily_old, other_daily], ignore_index=True)
daily_county.sort_values(["個案研判日", "縣市_顯示"], inplace=True)

min_date = daily_county["個案研判日"].min()
max_date = daily_county["個案研判日"].max()

# 建立 Dash App
app = Dash(__name__)

app.layout = html.Div([
    html.H2("臺灣目標縣市確診數趨勢", style={"font-family": "Microsoft JhengHei"}),

    html.H3("使用方式: 請至資料來源下載「Day_Confirmation_Age_County_Gender_19CoV.csv」，並與此.py檔放在同個目錄", style={"font-family": "Microsoft JhengHei"}),

    html.H4([
        "資料來源：",
        html.A("政府資料開放平台", 
            href="https://data.gov.tw/dataset/120711", 
            target="_blank",
            style={"color": "blue", "text-decoration": "underline"})
    ]),

    html.Div([
        html.Div([
            html.Label("選擇縣市1："),
            dcc.Dropdown(id='county-dropdown-1', options=dropdown_options, value=target_counties[0], clearable=True, style={"width": "200px"}),
        ]),
        html.Div([
            html.Label("選擇縣市2："),
            dcc.Dropdown(id='county-dropdown-2', options=dropdown_options, value=None, clearable=True, style={"width": "200px"}),
        ]),
        html.Div([
            html.Label("選擇縣市3："),
            dcc.Dropdown(id='county-dropdown-3', options=dropdown_options, value=None, clearable=True, style={"width": "200px"}),
        ]),
        html.Div([
            html.Label("選擇縣市4："),
            dcc.Dropdown(id='county-dropdown-4', options=dropdown_options, value=None, clearable=True, style={"width": "200px"}),
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

    try:
        start = pd.to_datetime(start_input)
        end = pd.to_datetime(end_input)
    except Exception:
        start = min_date
        end = max_date

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

    if start is None or end is None or start > end:
        start, end = min_date, max_date

    selected_counties = list({c for c in [c1, c2, c3, c4] if c})

    if not selected_counties:
        df_filtered = daily_county.iloc[0:0].copy()
    else:
        mask = (
            (daily_county["個案研判日"] >= start) &
            (daily_county["個案研判日"] <= end) &
            (daily_county["縣市_顯示"].isin(selected_counties))
        )
        df_filtered = daily_county.loc[mask].copy()

    df_filtered["累積確診數"] = df_filtered.groupby("縣市_顯示")["確定病例數"].cumsum()

    fig_daily = px.line(
        df_filtered,
        x="個案研判日",
        y="確定病例數",
        color="縣市_顯示",
        title="台灣目標縣市每日本土確診數"
    )
    fig_daily.update_layout(
        font=dict(family="Microsoft JhengHei", size=14),
        xaxis_title="日期",
        yaxis_title="每日本土確診數",
        legend_title="縣市",
        xaxis=dict(
            rangeslider=dict(visible=True),
            type="date",
            range=[start, end]
        )
    )

    fig_cum = px.line(
        df_filtered,
        x="個案研判日",
        y="累積確診數",
        color="縣市_顯示",
        title="台灣目標縣市累積本土確診數"
    )
    fig_cum.update_layout(
        font=dict(family="Microsoft JhengHei", size=14),
        xaxis_title="日期",
        yaxis_title="累積本土確診數",
        legend_title="縣市",
        xaxis=dict(
            rangeslider=dict(visible=True),
            type="date",
            range=[start, end]
        )
    )

    date_range_str = f"顯示日期區間：{start.date()} ~ {end.date()}"

    return fig_daily, fig_cum, date_range_str, str(start.date()), str(end.date())

@app.callback(
    Output("download-daily", "data"),
    Input("download-daily-btn", "n_clicks"),
    State('graph-daily', 'figure'),
    prevent_initial_call=True
)
def download_daily_png(n_clicks, figure):
    if figure is None:
        return dash.no_update
    fig = sanitize_figure(figure)
    img_bytes = pio.to_image(fig, format='png', scale=2)
    return dcc.send_bytes(img_bytes, "daily_confirmed.png")

@app.callback(
    Output("download-cum", "data"),
    Input("download-cum-btn", "n_clicks"),
    State('graph-cumulative', 'figure'),
    prevent_initial_call=True
)
def download_cum_png(n_clicks, figure):
    if figure is None:
        return dash.no_update
    fig = sanitize_figure(figure)
    img_bytes = pio.to_image(fig, format='png', scale=2)
    return dcc.send_bytes(img_bytes, "cumulative_confirmed.png")

if __name__ == "__main__":
    app.run(debug=True)
