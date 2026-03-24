import logging

import dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html

from app import (
    ARCHIVE_PAGE_INTERVAL_SECONDS,
    app,
)
from pages.archive_layout import (
    delete_snapshot,
    download_file,
    get_archive_data_star_num,
    get_archive_delete_layout,
    get_archive_table_layout,
    get_boolean_switch_layout,
    set_stars,
    update_table,
)

logger = logging.getLogger(__name__)
page_name = __name__.split(".")[-1]


def layout():
    star_on = False
    owner_on = True
    df_archive, n_stars = get_archive_data_star_num(
        page_name=page_name,
        star_on=star_on,
        owner_on=owner_on,
    )
    boolean_switch_layout = get_boolean_switch_layout(
        page_name=page_name,
        star_id="star-boolean-switch",
        star_on=star_on,
        owner_id="owner-boolean-switch",
        owner_on=owner_on,
    )
    archive_table_layout = get_archive_table_layout(
        page_name=page_name,
        aggrid_id="all-archive-table",
        rowData=df_archive.to_dict("records"),
    )
    archive_delete_layout = get_archive_delete_layout(
        delete_url_id="all-archive-delete-url",
        delete_button_id="all-archive-delete-button",
        download_button_id="all-archive-download-button",
        message_id="all-archive-delete-message",
    )
    return html.Div(
        children=[
            html.Div(
                "コントロールキーを押しながらクリックすることで複数選択することができます。",
                style={"margin": "12px", "font-size": "16px", "text-align": "left"},
            ),
            archive_table_layout,
            html.Div(
                children=[
                    boolean_switch_layout,
                ],
                style={
                    "display": "flex",
                    "flexDirection": "column",
                    # "justifyContent": "flex-start",
                    "alignItems": "flex-start",
                    "gap": "10px",
                    # "margin": "10px 0",
                },
            ),
            html.Div(
                children=[
                    dbc.Alert(
                        id="all-archive-star-message",
                        color="danger",
                        is_open=False,
                        className="alert",
                    ),
                ],
            ),
            archive_delete_layout,
            dcc.Interval(
                id="all-interval",
                interval=ARCHIVE_PAGE_INTERVAL_SECONDS * 1000,
                n_intervals=0,
            ),
        ]
    )


############################
# callbacks
############################


@app.callback(
    # NOTE: rowModelTypeがclientSideではない場合(Infiniteなど), OutputをrowDataではないものにする必要があるかも？
    # https://bpdash5.bp-test-de5.com/docs/dash-ag-grid/infinite-row-model
    Output("all-archive-table", "rowData"),
    Input("all-interval", "n_intervals"),
    Input("star-boolean-switch", "on"),
    Input("owner-boolean-switch", "on"),
)
def update_table_callback(_, star_on, owner_on):
    """intervalのカウントが増えるときやスイッチが押された時に、表示するデータを更新"""
    rowData, _ = update_table(
        page_name=page_name,
        star_on=star_on,
        owner_on=owner_on,
    )
    return rowData


@app.callback(
    Output("all-archive-star-message", "is_open", allow_duplicate=True),
    Output("all-archive-star-message", "color", allow_duplicate=True),
    Output("all-archive-star-message", "children", allow_duplicate=True),
    Output("all-archive-table", "rowData", allow_duplicate=True),
    Input("all-archive-table", "cellClicked"),
    State("all-archive-table", "rowData"),
    State("star-boolean-switch", "on"),
    State("owner-boolean-switch", "on"),
    prevent_initial_call=True,
)
def set_stars_callback(cell, data, star_on, owner_on):
    """星がクリックされた時にsnapshotのデータを更新したうえで、ag-gridのテーブル表示も更新する"""
    is_open, color, message, n_star_message, archive_data = set_stars(
        page_name=page_name,
        cell=cell,
        data=data,
        star_on=star_on,
        owner_on=owner_on,
    )
    return is_open, color, n_star_message, archive_data


@app.callback(
    Output("all-archive-table", "exportDataAsCsv"),
    Input("all-archive-download-button", "n_clicks"),
    prevent_initial_call=True,
)
def download_file_callback(n_clicks):
    """ダウンロードに対するコールバック"""
    return download_file(n_clicks)


@app.callback(
    Output("all-archive-table", "rowData", allow_duplicate=True),
    Output("all-archive-delete-message", "children", allow_duplicate=True),
    Input("all-archive-delete-button", "n_clicks"),
    State("all-archive-table", "selectedRows"),
    State("star-boolean-switch", "on"),
    State("owner-boolean-switch", "on"),
    prevent_initial_call=True,
)
def delete_snapshot_callback(n_clicks, selected_rows, star_on, owner_on):
    """結果削除のコールバック"""
    archive_data, delete_message = delete_snapshot(
        page_name=page_name,
        n_clicks=n_clicks,
        selected_rows=selected_rows,
        star_on=star_on,
        owner_on=owner_on,
    )
    return archive_data, delete_message
