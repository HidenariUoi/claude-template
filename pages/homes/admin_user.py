"""ユーザーの管理画面ページ"""

import dash_ag_grid as dag
import dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html, no_update
from dash_enterprise_libraries import ddk, dea

import database.auth.kc_client as kc_client
from app import app
from database.auth.auth_schema import (
    delete_auth_record,
    get_theme_and_sub_theme_name,
    read_hashed_data_names,
    update_auth,
)


def layout():
    keycloak_admin = kc_client.keycloak_admin
    groups = keycloak_admin.get_groups()
    list_group = [group["name"] for group in groups]
    # TODO: deaがcallback外なので治す
    current_user_name = dea.get_username()
    current_user_id = keycloak_admin.get_user_id(current_user_name)
    current_user_groups = [
        group["name"] for group in keycloak_admin.get_user_groups(current_user_id)
    ]
    layout = ddk.Block(
        children=[
            dbc.Modal(
                [
                    dbc.ModalHeader("追加したいユーザーの情報を入力してください。"),
                    dbc.ModalBody(
                        [
                            html.Div("ユーザー名:"),
                            dcc.Input(
                                id="add-user-name",
                                type="text",
                                placeholder="ユーザー名...",
                                className="mb-2",
                            ),
                            html.Div("メールアドレス:"),
                            dcc.Input(
                                id="add-email-address",
                                type="text",
                                placeholder="メールアドレス...",
                                className="mb-2",
                            ),
                            html.Div("グループ:"),
                            dcc.Dropdown(
                                list_group,
                                current_user_groups[0],
                                id="add-group-dropdown",
                                multi=False,
                            ),
                            html.Div("パスワード:"),
                            dcc.Input(
                                id="add-user-password",
                                type="text",
                                placeholder="パスワード...",
                                className="mb-2",
                            ),
                            html.Div("権限:"),
                            dbc.Checkbox(
                                "is-attach-admin-role", label="管理者権限を付与する", value=False
                            ),
                            html.Div(id="add-user-error"),
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button("ユーザー追加", id="add-user-button", color="success"),
                            dbc.Button("閉じる", id="close-add-user-modal", color="secondary"),
                        ]
                    ),
                ],
                id="add-user-modal",
                is_open=False,
            ),
            dbc.Modal(
                [
                    dbc.ModalHeader("本当に削除してもよろしいですか？"),
                    dbc.ModalBody(
                        id="deletion-body",
                        children="選択ユーザーを削除します。この作業は復元できません。",
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button("ユーザー削除", id="delete-user", color="success"),
                            dbc.Button("閉じる", id="close-deletion-modal", color="secondary"),
                        ]
                    ),
                ],
                id="deletion-modal",
                is_open=False,
            ),
            # Buttons Row
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Button("ユーザー追加", id="create-user", color="primary"), width="auto"
                    ),
                    dbc.Col(
                        dbc.Button("更新", id="refresh-user-list", color="primary", n_clicks=0),
                        width="auto",
                    ),
                ],
                className="mb-3 justify-content-start",  # Adds margin & aligns left
            ),
            # AG Grid Container
            dbc.Row(
                dbc.Col(
                    dag.AgGrid(
                        id="keycloak-users",
                        columnDefs=[
                            {
                                "field": "Name",
                                "headerName": "ユーザー名",
                                "sortable": True,
                                "flex": 1,
                            },
                            {
                                "field": "Email",
                                "headerName": "メールアドレス",
                                "sortable": True,
                                "flex": 1,
                            },
                            {
                                "field": "Group",
                                "headerName": "グループ",
                                "sortable": True,
                                "flex": 1,
                            },
                            {"field": "Roles", "headerName": "権限", "sortable": True, "flex": 1},
                            {
                                "field": "Delete",
                                "headerName": "ユーザー削除",
                                "cellRenderer": "Button",
                                "cellRendererParams": {
                                    "className": "btn btn-danger",
                                    "buttonText": "🗑️ 削除",
                                    "onClick": {
                                        "function": "delete_user",
                                        "params": {"action": "delete"},
                                    },
                                },
                            },
                        ],
                        style={"height": "500px", "width": "100%"},  # Limits height
                    ),
                    width=12,  # Full-width column
                )
            ),
        ]
    )

    return layout


@app.callback(
    Output("add-user-modal", "is_open", allow_duplicate=True),
    Input("create-user", "n_clicks"),
    State("add-user-modal", "is_open"),
    prevent_initial_call=True,
)
def open_model(click_data, is_open):
    return True


@app.callback(
    Output("add-user-modal", "is_open", allow_duplicate=True),
    Output("refresh-user-list", "n_clicks", allow_duplicate=True),
    Output("add-user-error", "children", allow_duplicate=True),
    Input("add-user-button", "n_clicks"),
    State("add-user-name", "value"),
    State("add-email-address", "value"),
    State("add-group-dropdown", "value"),
    State("add-user-password", "value"),
    State("is-attach-admin-role", "value"),
    State("refresh-user-list", "n_clicks"),
    prevent_initial_call=True,
)
def create_user(click_data, username, email, group, password, is_admin, n_clicks):
    roles = ["viewer"]
    if is_admin:
        roles.append("app-admin")

    print(f"Creating user: {username}, {email}, {group}, {password}, {roles}")

    success, err_msg = kc_client.create_user(
        username=username,
        email=email,
        group=group,
        password=password,
        roles=roles,
    )

    # TODO ユーザー追加に失敗した際、そのメッセージを表示

    print(f"Success: {success}")
    if success:
        list_data_name = read_hashed_data_names()
        for data_name in list_data_name:
            theme_name = get_theme_and_sub_theme_name(data_name)[0]
            update_auth(username, theme_name, is_admin)
    else:
        return True, [err_msg], no_update

    return False, no_update, n_clicks + 1


@app.callback(
    Output("add-user-modal", "is_open", allow_duplicate=True),
    Input("close-add-user-modal", "n_clicks"),
    prevent_initial_call=True,
)
def close_modal(clicked):
    return False  # Close the modal


@app.callback(
    Output("deletion-modal", "is_open", allow_duplicate=True),
    Input("close-deletion-modal", "n_clicks"),
    prevent_initial_call=True,
)
def close_deletion_modal(clicked):
    return False  # Close the modal


@app.callback(Output("keycloak-users", "rowData"), Input("refresh-user-list", "n_clicks"))
def refresh_user_list(click_data):
    keycloak_admin = kc_client.keycloak_admin
    current_user_name = dea.get_username()
    current_user_id = keycloak_admin.get_user_id(current_user_name)
    current_user_groups = [
        group["name"] for group in keycloak_admin.get_user_groups(current_user_id)
    ]

    tmp_users = kc_client.list_all_users()
    keycloak_admin = kc_client.keycloak_admin
    dash_client_id = keycloak_admin.get_client_id("dash")
    role_mapping = {"viewer": "ユーザー", "licensed_user": "開発者", "app-admin": "アプリ管理者"}
    users = []
    for user in tmp_users:
        user["Delete"] = (
            "削除" if user["Group"] == current_user_groups else ""
        )  # 同じグループのユーザーのみ削除可能
        user["Roles"] = ", ".join(
            role_mapping.get(role.strip(), role.strip())
            for role in user["Roles"].split(", ")
            if role.strip() in role_mapping.keys()
        )
        user_id = user["ID"]
        client_roles = keycloak_admin.get_client_roles_of_user(user_id, dash_client_id)
        if client_roles:
            users.append(user)
    return users


@app.callback(
    Output("deletion-modal", "is_open", allow_duplicate=True),  # Controls modal visibility
    Output("refresh-user-list", "n_clicks", allow_duplicate=True),
    Input("delete-user", "n_clicks"),
    State("keycloak-users", "rowData"),
    State("keycloak-users", "cellClicked"),
    State("refresh-user-list", "n_clicks"),
    prevent_initial_call=True,
)
def handle_delete_user(n_clicks, users, cell_clicked, n_refresh_clicks):
    if not cell_clicked or cell_clicked["colId"] != "Delete":
        return no_update, no_update

    idx = cell_clicked["rowIndex"]
    user = users[idx]

    if user["Delete"] != "削除":
        return no_update, no_update

    print(f"Deleting user: {user['Name']}")

    user_id = user["ID"]
    user_name = user["Name"]
    kc_client.delete_user(user_id)
    _ = delete_auth_record(user_name=user_name)

    return False, n_refresh_clicks + 1


@app.callback(
    Output("deletion-modal", "is_open", allow_duplicate=True),  # Controls modal visibility
    Output("deletion-body", "children"),
    Input("keycloak-users", "cellClicked"),
    State("keycloak-users", "rowData"),
    prevent_initial_call=True,
)
def toggle_modal(click_data, row_data):
    if click_data and click_data["colId"] == "Delete":
        idx = click_data["rowIndex"]
        user = row_data[idx]
        user_name = user["Name"]
        body_text = f"{user_name} を削除します。この作業は復元できません。"
        return True, body_text
    return no_update, no_update
