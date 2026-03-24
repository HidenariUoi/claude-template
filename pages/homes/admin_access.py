"""データの管理画面ページ"""

import os

import dash_ag_grid as dag
import dash_bootstrap_components as dbc
from dash import Input, Output, callback
from dash.exceptions import PreventUpdate

import database.auth.kc_client as kc_client
from database.auth.auth_schema import (
    get_access_info,
    update_auth,
)


def layout():
    columnDefs, auth_df = get_auth_df()

    return [
        dag.AgGrid(
            id="auth-table",
            columnDefs=columnDefs,
            rowData=auth_df.to_dict("records"),
            enableEnterpriseModules=True,
            licenseKey=os.environ.get("AG_LICENSE_KEY", ""),
            style={"height": "60vh", "margin": "16px"},
        ),
        dbc.Button(
            id="admin-user-loading-button",
            children="ユーザ情報更新",
            style={"margin-left": "16px"},
        ),
    ]


def get_auth_df():
    auth_df = get_access_info()
    auth_df = auth_df.pivot(columns="theme_name_ja", index="user_name", values="accessable").fillna(
        False
    )
    if len(auth_df) == 0:
        users = kc_client.list_all_users()
        list_user_name = [user["Name"] for user in users]
        auth_df.index = list_user_name
        auth_df = auth_df.rename_axis("user_name")

    columnDefs = [
        {
            "field": "user_name",
            "headerName": "ユーザ名 \\ テーマ名",  # noqa: W605
            "filter": True,
            "floatingFilter": True,
            "pinned": "left",
        }
    ] + [{"field": c, "headerName": c, "editable": True} for c in auth_df.columns]
    auth_df = auth_df.reset_index()

    return columnDefs, auth_df


@callback(
    Output("auth-table", "columnDefs"),
    Output("auth-table", "rowData"),
    Input("auth-table", "cellValueChanged"),
    prevent_initial_call=True,
)
def change_auth(cell):
    user_name = cell[0]["data"]["user_name"]
    accessable = cell[0]["value"]
    theme_name_ja = cell[0]["colId"]
    update_auth(user_name, theme_name_ja, accessable)
    raise PreventUpdate


@callback(
    Output("auth-table", "columnDefs", allow_duplicate=True),
    Output("auth-table", "rowData", allow_duplicate=True),
    Input("admin-user-loading-button", "n_clicks"),
    prevent_initial_call=True,
)
def call_update_user_data(n_clicks):
    if (n_clicks is None) or (n_clicks == 0):
        raise PreventUpdate

    columnDefs, auth_df = get_auth_df()
    return columnDefs, auth_df.to_dict("records")
