"""エラー画面のレイアウト
"""
import dash_design_kit as ddk
from dash import html
from app import snap

def layout(snapshot_id, error_msg):
    return ddk.Card([
        html.H1("Error"),
        html.P(error_msg),
    ])