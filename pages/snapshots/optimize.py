"""最適化結果画面のレイアウト
"""
import io
import pandas as pd
import dash_design_kit as ddk
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State
from app import app, snap


def layout(snapshot_id, job_name):
    return ddk.Card([
        dcc.Download(id="optimize-result-download"),
        html.Button(
            "結果ダウンロード",
            id="optimize-result-download-button",
            style={
                "backgroundColor": "green",
                "border": "2px solid green",
            },
        ),
        html.Div(id="optimize-result-download-store", style={"display": "none"}, children=snapshot_id),
    ])


@app.callback(
    Output("optimize-result-download", "data"),
    Input("optimize-result-download-button", "n_clicks"),
    State("optimize-result-download-store", "children"),
    prevent_initial_call=True,
)
def download_result(n_clicks, snapshot_id):
    """結果をエクセルファイルとしてダウンロードする"""
    if not n_clicks:
        return None

    # TODO: snapshot_idをもとに結果データを取得する
    df = pd.DataFrame()

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="結果")
    buffer.seek(0)

    return dcc.send_bytes(buffer.read(), filename=f"result_{snapshot_id}.xlsx")
