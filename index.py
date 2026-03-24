import dash_bootstrap_components as dbc
from dash import Input, Output, State, clientside_callback, dcc, html, no_update
from dash_enterprise_libraries import ddk

import schedules.delete_data  # noqa: F401
from app import SPECIFICATION_URL, TABLE_DEFINITION_URL, app, snap
from database.auth.auth_schema import (
    check_table_exist,
    get_theme_and_sub_theme_name,
    check_material_encoder_exist,
)
from pages import archive, home, optimize, snapshot
from schedules import delete_data  # noqa: F401

server = app.server
celery_instance = snap.celery_instance
celery_instance.conf.timezone = "Asia/Tokyo"

app.layout = ddk.App(
    show_editor=False,
    children=[
        ddk.Header(
            [
                dcc.Link(
                    href=app.get_relative_path("/"),
                    children=[
                        ddk.Logo(
                            src=app.get_relative_path(
                                "/assets/logo/Experimental Design Simulator 300_60.png"
                            ),
                        ),
                    ],
                ),
                html.Span(
                    [
                        html.Div(
                            [
                                ddk.Icon(
                                    icon_name="industry",
                                    className="icon-sm",
                                ),
                                html.Span(
                                    "テーマ名",
                                    className="icon-sm",
                                    style={"paddingLeft": "0.25rem"},
                                ),
                            ],
                            style={"padding": "0 15px 0 20px"},
                        ),
                        ddk.Title(id="theme-name-header"),
                    ],
                    id="theme-name-span",
                    style={"display": "none"},
                ),
                html.Span(
                    [
                        html.Div(
                            [
                                ddk.Icon(
                                    icon_name="folder-open",
                                    className="icon-sm",
                                ),
                                html.Span(
                                    "サブテーマ名",
                                    className="icon-sm",
                                    style={"paddingLeft": "0.25rem"},
                                ),
                            ],
                            style={"padding": "0 15px 0 20px"},
                        ),
                        ddk.Title(id="sub-theme-name-header"),
                    ],
                    id="sub-theme-name-span",
                    style={"display": "none"},
                ),
                dcc.Store(id="hashed-data-name-store", storage_type="session"),
                html.Span(
                    [
                        html.Div(
                            [
                                ddk.Icon(
                                    icon_name="folder",
                                    icon_category="regular",
                                    className="icon-sm",
                                ),
                                html.Span(
                                    "ジョブ名",
                                    className="icon-sm",
                                    style={"paddingLeft": "0.25rem"},
                                ),
                            ],
                            style={"padding": "0 15px 0 20px"},
                        ),
                        ddk.Title(id="job-name-header"),
                        dcc.Store(id="job-name-store", storage_type="session"),
                    ],
                    id="job-name-span",
                    style={"display": "none"},
                ),
                ddk.Menu(
                    [
                        dcc.Link(
                            dbc.Button(
                                "使い方マニュアル",
                                id="specification-button",
                                color="success",
                                style={"display": "none"},
                            ),
                            href=SPECIFICATION_URL,
                            target="_blank",
                        ),
                        dcc.Link(
                            dbc.Button(
                                "サンプルデータ",
                                id="table-definition-button",
                                color="success",
                                style={"display": "none"},
                            ),
                            href=TABLE_DEFINITION_URL,
                            target="_blank",
                        ),
                    ]
                ),
            ],
            background_color="#aacc66",
            style={"z-index": 0},
        ),
        ddk.Sidebar(
            id="sidebar",
            foldable=False,
            style={"maxWidth": "250px", "display": "none"},
            children=[
                ddk.Title(
                    children=[
                        "XX最適化",
                        html.Br(),
                        "シミュレータ",
                    ],
                    style={"width": "250px"},
                ),
                ddk.Menu(
                    id="sidebar-menu",
                    children=[
                        html.Div(
                            id="sidebar-fold-button",
                            children=[
                                ddk.Icon(
                                    id="sidebar-fold-button-icon",
                                    icon_name="angle-left",
                                    icon_color="#5fade2",
                                ),
                            ],
                            style={
                                "fontSize": "25px",
                                "width": "100%",
                                "margin": "20px auto 20px auto",
                                "cursor": "pointer",
                                "textAlign": "center",
                            },
                        ),
                        dcc.Link(
                            href=app.get_relative_path("/optimize"),
                            children=[
                                ddk.Icon(icon_name="flask"),
                                "最適化実行",
                            ],
                            id="sidebar-optimize-menu",
                            style={"white-space": "nowrap"},
                        ),
                        dcc.Link(
                            href=app.get_relative_path("/archive"),
                            children=[ddk.Icon(icon_name="archive"), "実行履歴"],
                            id="sidebar-archive-menu",
                            style={"whiteSpace": "nowrap"},
                        ),
                    ],
                ),
                dcc.Store(id="sidebar-dummy"),
                dcc.Store(id="num-refresh", data=0),
            ],
        ),
        ddk.SidebarCompanion(
            children=[
                dcc.Location(id="url", refresh="callback-nav"),
                html.Div(
                    id="content",
                    style={"minHeight": "100vh", "marginBottom": "100px"},
                ),
            ],
        ),
    ],
)


@app.callback(
    [
        Output("content", "children"),
        Output("job-name-header", "children"),
        # Output("theme-name-span", "style"),
        # Output("sub-theme-name-span", "style"),
        # Output("job-name-span", "style"),
        # Output("specification-button", "style"),
        # Output("table-definition-button", "style"),
        # Output("sidebar", "style"),
        # Output("sidebar-register-menu", "style"),
        # Output("sidebar-dashboard-menu", "style"),
        # Output("sidebar-predict-menu", "style"),
        # Output("sidebar-optimize-menu", "style"),
        # Output("sidebar-archive-menu", "style"),
    ],
    Input("url", "pathname"),
    Input("num-refresh", "data"),
    State("hashed-data-name-store", "data"),
)
def display_content(path_name, refresh_flag, data_name):
    page_name = app.strip_relative_path(path_name)

    num_sidebar_items = 2  # 最適化、実行履歴
    num_header_items = 3  # テーマ名、サブテーマ名、ジョブ名
    num_doc_items = 2  # マニュアル、サンプルデータ
    # ヘッダー、サイドバーの表示設定
    if page_name == "home" or not page_name:
        header_name_style = [{"display": "none"}] * num_header_items
        header_doc_style = [{"display": "block"}] * num_doc_items
        sidebar_style = [{"display": "none"}]
    else:
        header_name_style = [{"display": "block"}] * num_header_items
        header_doc_style = [{"display": "none"}] * num_doc_items
        sidebar_style = [{"display": "block"}]
    # 表示コンテンツの切替
    if page_name == "home" or not page_name:  # None or ''
        page_layout = home.layout()
        job_name = ""
    elif page_name == "optimize":
        page_layout = optimize.layout(data_name)
        job_name = ""
    elif page_name == "archive":
        page_layout = archive.layout(data_name)
        job_name = ""
    elif page_name.startswith("snapshot-"):
        contents, data_name, job_name = snapshot.layout(page_name)
        page_layout = contents
    else:
        return "404", "Not Found"

    # # サイドバーのメニュー表示設定
    # if data_name is not None:
    #     is_encoder_exist = check_material_encoder_exist(hashed_data_name=data_name)
    #     if is_encoder_exist:
    #         sidebar_menu_style = [{"whiteSpace": "nowrap"}] * num_sidebar_items
    #     else:
    #         # データ登録と実行履歴のみ表示
    #         sidebar_menu_style = (
    #             [{"whiteSpace": "nowrap"}]
    #             + [{"display": "none"}, {"display": "none"}, {"display": "none"}]
    #             + [{"whiteSpace": "nowrap"}]
    #         )
    # else:
    #     sidebar_menu_style = [{"display": "none"}] * num_sidebar_items

    return page_layout, job_name


@app.callback(
    Output("theme-name-header", "children"),
    Output("sub-theme-name-header", "children"),
    Input("hashed-data-name-store", "data"),
)
def update_header_data_name(data_name):
    """データ名の更新時、ヘッダのテーマ名を更新"""
    names = get_theme_and_sub_theme_name(data_name)
    if all(names) is None:
        theme_name, sub_theme_name = "", ""
    else:
        theme_name, sub_theme_name = names
    return theme_name, sub_theme_name


@app.callback(
    Output("hashed-data-name-store", "data", allow_duplicate=True),
    Input("url", "pathname"),
    prevent_initial_call=True,
)
def set_data_name_from_snapshot(path_name):
    """url更新時にdata_nameのstoreを更新"""
    page_name = app.strip_relative_path(path_name)
    if not page_name.startswith("snapshot-"):
        return no_update

    data_job_name = snapshot.get_data_job_name_from_snap(page_name)
    if data_job_name is None:
        return no_update
    return data_job_name[0]


clientside_callback(
    """
    function (click) {
        document.querySelector('#sidebar .sidebar--content').toggleAttribute('folded');
        var current_folded_state = document.querySelector('#sidebar #menu').getAttribute('data-folded');
        var new_folded_state = (current_folded_state === 'false') ? 'true' : 'false';
        document.querySelector('#sidebar #menu').setAttribute('data-folded', new_folded_state);
        return 'dummy';
    }
    """,
    Output("sidebar-dummy", "data"),
    Input("sidebar-fold-button", "n_clicks"),
    prevent_initial_call=True,
)
clientside_callback(
    """
    function (click, current_children) {
        return (current_children === 'angle-left') ? 'angle-right' : 'angle-left';
    }
    """,
    Output("sidebar-fold-button-icon", "icon_name"),
    Input("sidebar-fold-button", "n_clicks"),
    State("sidebar-fold-button-icon", "icon_name"),
    prevent_initial_call=True,
)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", use_reloader=True)
