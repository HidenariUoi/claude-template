"""データ管理ページ"""

import json

import dash_bootstrap_components as dbc
from dash import (
    ALL,
    MATCH,
    Input,
    Output,
    State,
    callback_context,
    dcc,
    html,
    set_props,
)
from dash.exceptions import PreventUpdate
from dash_enterprise_libraries import ddk, dea

from app import app
from database.auth.auth_schema import (
    add_data_name,
    check_material_encoder_exist,
    get_list_accessable_data_info,
    hash_data_name,
    validate_data_name,
    validate_theme_name,
)


def _get_data_card(theme_name, sub_theme_name, description, tags, pos):
    description = description if description else "説明がありません"
    if not tags:  # タグが存在しない場合にレイアウトを保つため透明なバッジを配置
        tags = [
            dbc.Badge(
                "\u00a0", color="primary", className="me-1 custom-badge", style={"opacity": 0}
            )
        ]
    else:
        tags = [dbc.Badge(tag, color="primary", className="me-1 custom-badge") for tag in tags]

    card_layout = [
        dbc.CardHeader(
            children=[
                html.Div(
                    id={"type": "dynamic-theme-name", "index": pos},
                    children=[theme_name],
                    style={"display": "none"},
                ),
                html.Div(
                    id={"type": "dynamic-sub-theme-name", "index": pos},
                    children=sub_theme_name,
                    style={"display": "inline-block", "fontSize": "1.25rem"},
                ),
            ],
            style={
                "backgroundColor": "#f8f9fa",
                "fontWeight": "bold",
                "fontSize": "1.25rem",
                "padding": "1.2rem",
            },
        ),
        dbc.CardBody(
            html.P(description, className="card-text"),
            style={"padding": "0.75rem", "overflow": "hidden", "flex": "1"},
        ),
        dbc.CardFooter(
            tags,
            className="bg-white d-flex align-items-center",
            style={"padding": "1.2rem"},
        ),
    ]

    return html.Div(
        children=[
            dbc.Card(card_layout, className="mb-4", style={"height": "100%"}),
            html.Button(  # カードをクリックした際に選択される隠しボタン
                id={"type": "select-data-name-button", "index": pos},
                style={  # 親要素と同じ大きさで透明のボタンを配置
                    "position": "absolute",
                    "top": 0,
                    "left": 0,
                    "width": "100%",
                    "height": "100%",
                    "opacity": 0,
                    "cursor": "pointer",
                },
            ),
        ],
        style={"position": "relative"},
    )


def layout():
    modal_layout = ddk.Modal(
        children=[
            html.Button(
                children=[
                    ddk.Icon(icon_name="flask"),
                    "テーマ追加",
                ],
                id={"type": "register-modal-button", "index": 0},
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "backgroundColor": "green",
                    "color": "white",
                    "fontSize": "20px",
                },
            ),
            html.Div(
                id={
                    "type": "data-name-register-modal",
                    "index": 0,
                },
                children=ddk.Block(
                    children=_register_form_layout(index=0),
                    style={"width": "100%", "overflow": "auto"},
                ),
                style={"width": "50%"},
            ),
        ],
        hide_target=True,
        target_id={
            "type": "data-name-register-modal",
            "index": 0,
        },
        style={"width": "50%", "height": "80%", "overflow": "hidden"},
    )

    # フィルターを横並びに変更
    filter_row = dbc.Row(
        [
            dbc.Col(
                dcc.Dropdown(
                    id="theme-filter-dropdown",
                    options=[],
                    placeholder="テーマ名でフィルター",
                    clearable=True,
                    multi=True,
                ),
                width=3,
            ),
            dbc.Col(
                dbc.InputGroup(
                    [
                        dbc.InputGroupText(
                            html.I(className="fa fa-search"),  # Font Awesomeの虫眼鏡アイコン
                            style={"backgroundColor": "#f8f9fa"},  # アイコンの背景色を調整
                        ),
                        dbc.Input(
                            id="sub-theme-filter-input",
                            type="text",
                            placeholder="サブテーマ名でフィルター",
                        ),
                    ],
                    style={"width": "100%"},
                    className="mb-3",
                ),
                width=3,
            ),
            dbc.Col(
                dcc.Dropdown(
                    id="tag-filter-dropdown",
                    options=[],  # 初期値として選択可能なタグを設定
                    placeholder="タグでフィルター",
                    clearable=True,
                    multi=True,
                ),
                width=3,
            ),
            dbc.Col(
                html.Button(
                    "フィルターをリセット",
                    id="reset-filters-button",
                    style={
                        "backgroundColor": "gray",
                        "color": "white",
                        "border": "none",
                        "padding": "10px 20px",
                        "borderRadius": "5px",
                        "cursor": "pointer",
                    },
                ),
                width=3,
            ),
        ],
        className="mb-4",
    )

    layout = html.Div(
        [
            modal_layout,
            filter_row,  # フィルターを横並びに配置
            ddk.ControlCard(
                id="theme-layout",
                orientation="horizontal",
                style={"border": "none", "boxShadow": "none"},
                children=[],
            ),
        ]
    )
    return layout


@app.callback(
    Output("theme-filter-dropdown", "value"),
    Output("sub-theme-filter-input", "value"),
    Output("tag-filter-dropdown", "value"),
    Input("reset-filters-button", "n_clicks"),
    prevent_initial_call=True,
)
def reset_filters(n_clicks):
    if n_clicks is None or n_clicks == 0:
        raise PreventUpdate
    return [], "", []


@app.callback(
    Output("theme-layout", "children", allow_duplicate=True),
    Input("url", "pathname"),
    Input("home-tabs", "active_tab"),
    Input("theme-filter-dropdown", "value"),
    Input("sub-theme-filter-input", "value"),
    Input("tag-filter-dropdown", "value"),
    prevent_initial_call="initial_duplicate",
)
def update_theme_cards(path_name, tab_id, selected_themes, sub_theme_filter, selected_tags):
    page_name = app.strip_relative_path(path_name)
    # ホームのページで、テーマ選択のタブを開いている時以外は更新しない
    if not (tab_id == "theme-tab" and (page_name == "home" or not page_name)):  # "" or Noneはホーム
        raise PreventUpdate

    user_name = dea.get_username()
    list_data_info = get_list_accessable_data_info(user_name)

    # フィルターの適用
    if selected_themes:
        list_data_info = [di for di in list_data_info if di.theme_name_ja in selected_themes]
    if sub_theme_filter:  # サブテーマ名に入力した文字列と部分一致
        list_data_info = [di for di in list_data_info if sub_theme_filter in di.sub_theme_name_ja]
    if selected_tags:
        list_data_info = [
            di for di in list_data_info if any(tag in di.tags for tag in selected_tags)
        ]

    # テーマ名ごとにデータをグループ化
    grouped_data = {}
    for di in list_data_info:
        if di.theme_name_ja not in grouped_data:
            grouped_data[di.theme_name_ja] = []
        grouped_data[di.theme_name_ja].append(di)

    # グループ化されたデータを基にレイアウトを作成
    exist_data_cards_layout = []
    theme_pos = 1
    data_pos = 0
    for theme_name, data_list in grouped_data.items():
        # テーマ名のヘッダーを追加
        exist_data_cards_layout.append(
            html.Div(
                children=[
                    html.Div(
                        theme_name,
                        style={
                            "fontWeight": "bold",
                            "fontSize": "1.5rem",
                            "whiteSpace": "nowrap",
                            "textOverflow": "ellipsis",
                            "overflow": "hidden",
                            "paddingBottom": "4px",
                            "width": "100%",
                        },
                    ),
                    ddk.Modal(
                        children=[
                            html.Button(
                                children=[
                                    ddk.Icon(icon_name="folder"),
                                    "サブテーマ追加",
                                ],
                                id={"type": "register-modal-button", "index": theme_pos},
                                style={
                                    "display": "inline-flex",
                                    "alignItems": "center",
                                    "justifyContent": "center",
                                    "backgroundColor": "primary",
                                    "color": "white",
                                    "whiteSpace": "nowrap",
                                    "fontSize": "14px",
                                    "padding": "2px 12px",
                                },
                            ),
                            html.Div(
                                id={"type": "data-name-register-modal", "index": theme_pos},
                                children=ddk.Block(
                                    children=_register_form_layout(
                                        theme_name=theme_name,
                                        index=theme_pos,
                                    ),
                                    style={"width": "100%", "overflow": "auto"},
                                ),
                                style={"width": "50%"},
                            ),
                        ],
                        hide_target=True,
                        target_id={"type": "data-name-register-modal", "index": theme_pos},
                        style={"height": "80%", "width": "50%", "overflow": "hidden"},
                    ),
                ],
                style={
                    "display": "flex",
                    "flexDirection": "column",
                    "alignItems": "flex-start",
                    "marginBottom": "0.25rem",
                    "gap": "0.25rem",
                    "width": "100%",
                },
            )
        )
        exist_data_cards_layout.append(ddk.ControlItem(width=100))
        # 各データカードを追加
        for di in data_list:
            exist_data_cards_layout.append(
                ddk.ControlItem(
                    _get_data_card(
                        di.theme_name_ja,
                        di.sub_theme_name_ja,
                        di.description,
                        di.tags,
                        data_pos,
                    ),
                    width=1 / 4,
                )
            )
            data_pos += 1  # data_posをインクリメント
        # テーマごとの区切り線を追加
        exist_data_cards_layout.append(
            html.Div(
                style={
                    "borderBottom": "1px solid #dee2e6",
                    "margin": "1rem 0",
                    "width": "100%",
                }
            )
        )
        theme_pos += 1  # theme_posをインクリメント

    return exist_data_cards_layout


@app.callback(
    Output("tag-filter-dropdown", "options", allow_duplicate=True),
    Output({"type": "existing-tags-dropdown", "index": ALL}, "options"),
    Input("url", "pathname"),
    Input("home-tabs", "active_tab"),
    prevent_initial_call="initial_duplicate",
)
def update_tag_filter_options(path_name, tab_id):
    page_name = app.strip_relative_path(path_name)
    if not (tab_id == "theme-tab" and (page_name == "home" or not page_name)):
        raise PreventUpdate  # 条件に合致しない場合は更新を停止

    user_name = dea.get_username()
    list_data_info = get_list_accessable_data_info(user_name)

    # タグ一覧を取得
    tags = sorted({tag for di in list_data_info for tag in di.tags})
    options = [{"label": tag, "value": tag} for tag in tags]
    return options, [options] * len(callback_context.outputs_list[1])


@app.callback(
    Output("theme-filter-dropdown", "options", allow_duplicate=True),
    Input("url", "pathname"),
    Input("home-tabs", "active_tab"),
    prevent_initial_call="initial_duplicate",
)
def update_factory_filter_options(path_name, tab_id):
    page_name = app.strip_relative_path(path_name)
    if not (tab_id == "theme-tab" and (page_name == "home" or not page_name)):
        raise PreventUpdate  # 条件に合致しない場合は更新を停止

    user_name = dea.get_username()
    list_data_info = get_list_accessable_data_info(user_name)

    # テーマ名一覧を取得
    themes = sorted({di.theme_name_ja for di in list_data_info})
    return [{"label": theme, "value": theme} for theme in themes]


@app.callback(
    [
        Output("hashed-data-name-store", "data"),
        Output("url", "href", allow_duplicate=True),
    ],
    Input({"type": "select-data-name-button", "index": ALL}, "n_clicks"),
    State({"type": "dynamic-theme-name", "index": ALL}, "children"),
    State({"type": "dynamic-sub-theme-name", "index": ALL}, "children"),
    prevent_initial_call=True,
)
def update_data_name(button_clicks, theme_names, sub_theme_names):
    # どのボタンがクリックされたか確認
    ctx = callback_context
    if not ctx.triggered or ctx.triggered[0]["prop_id"] == "." or not any(button_clicks):
        raise PreventUpdate

    # クリックされたボタンのIDを取得
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
    button_id = json.loads(triggered_id)  # 動的IDを取得
    index = button_id.get("index", 0)
    theme_name = theme_names[index][0]
    sub_theme_name = sub_theme_names[index]
    data_name = hash_data_name(theme_name, sub_theme_name)

    return data_name, app.get_relative_path("/optimize")


def _register_form_layout(index, theme_name=None, sub_theme_name=None):
    if index is None:
        raise ValueError("index must be provided and cannot be None")

    layout = [
        ddk.CardHeader(title="新たにサブテーマを登録できます"),
        ddk.ControlItem(
            label="テーマ名を入力してください",
            children=[
                dcc.Input(
                    id={"type": "register-theme-name", "index": index},
                    placeholder="テーマ名",
                    value=theme_name,  # 初期値を設定
                    disabled=theme_name is not None,  # 初期値が設定されている場合は編集不可
                )
            ],
        ),
        ddk.ControlItem(
            label="サブテーマ名を入力してください",
            children=[
                dcc.Input(
                    id={"type": "register-sub-theme-name", "index": index},
                    placeholder="サブテーマ名",
                    value=sub_theme_name,  # 初期値を設定
                    disabled=sub_theme_name is not None,  # 初期値が設定されている場合は編集不可
                )
            ],
        ),
        ddk.ControlItem(
            label="説明を入力してください（任意）",
            children=[
                dcc.Input(
                    id={"type": "register-description", "index": index},
                    placeholder="説明",
                )
            ],
        ),
        ddk.ControlItem(
            label="タグを入力してください（任意）",
            children=[
                dbc.Row(
                    [
                        dbc.Col(
                            dbc.Input(
                                id={"type": "register-tags-input", "index": index},
                                type="text",
                                placeholder="新しいタグを作成",
                            ),
                            width=5,
                        ),
                        dbc.Col(
                            dcc.Dropdown(
                                id={"type": "existing-tags-dropdown", "index": index},
                                options=[],
                                placeholder="候補タグを選択",
                                clearable=True,
                                multi=True,
                            ),
                            width=5,
                        ),
                        dbc.Col(
                            ddk.ControlItem(
                                children=[
                                    dbc.Button(
                                        "追加",
                                        id={"type": "add-tag-button", "index": index},
                                        color="primary",
                                        style={"height": "100%"},
                                    ),
                                ]
                            ),
                            width=2,
                        ),
                    ],
                    style={"width": "100%", "alignItems": "center"},
                ),
            ],
        ),
        ddk.ControlItem(
            children=[
                html.Div(
                    id={"type": "register-tags-list", "index": index},
                    children=[],
                ),
            ]
        ),
        dbc.Alert(
            id={"type": "register-data-name-validate-message", "index": index},
            color="warning",
            is_open=False,
        ),
        ddk.ControlItem(
            children=[
                dbc.Button(
                    id={"type": "register-data-name-button", "index": index},
                    children="登録",
                    n_clicks=0,
                    disabled=True,
                ),
            ]
        ),
    ]
    return layout


# タグ追加コールバック
@app.callback(
    Output({"type": "register-tags-list", "index": MATCH}, "children"),
    Output({"type": "register-tags-input", "index": MATCH}, "value"),
    Output({"type": "existing-tags-dropdown", "index": MATCH}, "value"),
    [
        Input({"type": "add-tag-button", "index": MATCH}, "n_clicks"),
        Input({"type": "register-tags-input", "index": MATCH}, "n_submit"),
    ],
    [
        State({"type": "register-tags-input", "index": MATCH}, "value"),
        State({"type": "existing-tags-dropdown", "index": MATCH}, "value"),
        State({"type": "register-tags-list", "index": MATCH}, "children"),
    ],
    prevent_initial_call=True,
)
def update_tag_list(n_clicks, n_submit, new_tag, select_tags, current_tags):
    # 入力フォームとドロップダウン値から追加するタグのリストを作成
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    tags_to_add = []
    # 既に設定されているタグは追加しない
    if new_tag and new_tag not in [tag["props"]["id"]["value"] for tag in current_tags]:
        tags_to_add.append(new_tag)
    if select_tags:
        for tag in select_tags:
            if tag not in [t["props"]["id"]["value"] for t in current_tags]:
                tags_to_add.append(tag)

    for tag in tags_to_add:
        current_tags.append(
            dbc.Badge(
                [
                    tag,
                    html.Span(
                        "×",
                        style={
                            "marginLeft": "8px",
                            "cursor": "pointer",
                            "color": "lightgray",
                            "fontWeight": "bold",
                        },
                    ),
                ],
                color="primary",
                className="me-1 custom-badge",
                style={"cursor": "pointer"},
                id={"type": "tag-badge", "value": tag},
            )
        )

    return current_tags, "", []


# タグ削除コールバック
@app.callback(
    Output({"type": "register-tags-list", "index": MATCH}, "children", allow_duplicate=True),
    Input({"type": "tag-badge", "value": ALL}, "n_clicks"),
    State({"type": "register-tags-list", "index": MATCH}, "children"),
    prevent_initial_call=True,
)
def remove_tag(n_clicks, current_tags):
    if all(click is None for click in n_clicks):
        raise PreventUpdate
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate

    # クリックされたタグを削除
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
    tag_to_remove = json.loads(triggered_id)["value"]
    updated_tags = [tag for tag in current_tags if tag["props"]["id"]["value"] != tag_to_remove]
    return updated_tags


@app.callback(
    Output({"type": "register-data-name-validate-message", "index": MATCH}, "color"),
    Output({"type": "register-data-name-validate-message", "index": MATCH}, "children"),
    Output({"type": "register-data-name-validate-message", "index": MATCH}, "is_open"),
    Output({"type": "register-data-name-button", "index": MATCH}, "disabled"),
    Input({"type": "register-theme-name", "index": MATCH}, "n_blur"),
    Input({"type": "register-sub-theme-name", "index": MATCH}, "n_blur"),
    State({"type": "register-theme-name", "index": MATCH}, "value"),
    State({"type": "register-sub-theme-name", "index": MATCH}, "value"),
    prevent_initial_call=True,
)
def validate_input_data_name(th_n_blur, sub_n_blur, theme_name, sub_theme_name):
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
    index = json.loads(triggered_id)["index"]

    if index == 0:
        if theme_name == "" or theme_name is None:
            return "success", "", False, True
        message = validate_theme_name(theme_name)
        if message == "":
            is_passed = sub_theme_name not in [None, ""]
            message = "サブテーマ名を入力してください"
        else:
            is_passed = False
    else:
        if sub_theme_name == "" or sub_theme_name is None or theme_name == "" or theme_name is None:
            return "success", "", False, True
        message = validate_data_name(theme_name, sub_theme_name)
        is_passed = message == ""

    message = "サブテーマを登録できます" if is_passed else message
    message_color = "success" if is_passed else "danger"
    disabled = False if is_passed else True

    return message_color, message, True, disabled


@app.callback(
    Output(
        {"type": "register-data-name-validate-message", "index": ALL},
        "color",
        allow_duplicate=True,
    ),
    Output(
        {"type": "register-data-name-validate-message", "index": ALL},
        "children",
        allow_duplicate=True,
    ),
    Output(
        {"type": "register-data-name-validate-message", "index": ALL},
        "is_open",
        allow_duplicate=True,
    ),
    Output({"type": "register-data-name-button", "index": ALL}, "disabled", allow_duplicate=True),
    Output("url", "href", allow_duplicate=True),
    Output("hashed-data-name-store", "data", allow_duplicate=True),
    Input({"type": "register-data-name-button", "index": ALL}, "n_clicks"),
    State({"type": "register-theme-name", "index": ALL}, "value"),
    State({"type": "register-sub-theme-name", "index": ALL}, "value"),
    State({"type": "register-description", "index": ALL}, "value"),
    State({"type": "register-tags-list", "index": ALL}, "children"),
    prevent_initial_call=True,
)
def register_data_name(n_clicks, theme_names, sub_theme_names, descriptions, tag_children_list):
    ctx = callback_context
    if not ctx.triggered or not any(n_clicks):
        raise PreventUpdate

    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
    button_id = json.loads(triggered_id)  # 動的IDを取得
    index = button_id["index"]

    if n_clicks[index] == 0:
        raise PreventUpdate
    set_props(ctx.triggered_id, {"disabled": True})  # 登録中ボタンクリック不可

    theme_name = theme_names[index]
    sub_theme_name = sub_theme_names[index]
    description = descriptions[index]
    tags = [tag["props"]["id"]["value"] for tag in tag_children_list[index]]

    add_data_name(theme_name, sub_theme_name, tags, description)
    hashed_data_name = hash_data_name(theme_name, sub_theme_name)

    return (
        ["success" if i == index else "warning" for i in range(len(n_clicks))],
        ["登録が完了しました" if i == index else "待機中" for i in range(len(n_clicks))],
        [True if i == index else False for i in range(len(n_clicks))],
        [True] * len(n_clicks),
        app.get_relative_path("/optimize"),
        hashed_data_name,
    )
