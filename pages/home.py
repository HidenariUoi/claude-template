import dash_bootstrap_components as dbc
from dash import Input, Output, html
from dash_enterprise_libraries import ddk, dea
from flask import request

from app import app
from database.auth.jwks_client import get_is_app_admin
from pages.homes import admin_access, admin_user, all_snapshot, theme


def layout():
    user_name = dea.get_username()
    children = [
        dbc.Tab(label="登録テーマ管理", tab_id="theme-tab"),
        dbc.Tab(label="全実行履歴", tab_id="all-snapshot-tab"),
    ]
    if user_name:
        is_admin = get_is_app_admin(request)
        if is_admin:
            children.append(dbc.Tab(label="ユーザー管理", tab_id="admin-user-tab"))
            children.append(dbc.Tab(label="アクセス権限管理", tab_id="admin-access-tab"))

    return ddk.ControlCard(
        children=[
            dbc.Tabs(id="home-tabs", active_tab="theme-tab", children=children),
            html.Div(id="home-tab-content"),
        ],
    )


@app.callback(
    Output("home-tab-content", "children"),
    Input("home-tabs", "active_tab"),
    prevent_initial_call=False,
)
def update_theme_tab_content(tab_id):
    if tab_id == "theme-tab":
        return theme.layout()

    elif tab_id == "admin-user-tab":
        return admin_user.layout()

    elif tab_id == "admin-access-tab":
        return admin_access.layout()

    elif tab_id == "all-snapshot-tab":
        return all_snapshot.layout()

    return "No tab selected"
