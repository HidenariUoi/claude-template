"""Ag-gridを利用したarchive-tableを作成する
"""
import os
import shutil
import pandas as pd
import dash_ag_grid as dag
import dash
import dash_bootstrap_components as dbc
import dash_enterprise_auth as dea
from dash import dcc, html
from dash.dependencies import Input, Output, State

from app import (
    snap,
    app,
    ARCHIVE_PAGE_INTERVAL_SECONDS,
    ARCHIVE_PAGE_SIZE,
)


ARCHIVE_TABLE_COLUMN_DEF = [
    {"field": "id", "headerName": "id", "checkboxSelection": True},
    {
        "field": "snapshot_id",
        "headerName": "ステータス",
        "cellRenderer": "markdown",
    },
    {"field": "error", "headerName": "エラーメッセージ"},
    {"field": "username", "headerName": "実行者"},
    {"field": "created_time", "headerName": "実行日付"},
    {"field": "job-id", "headerName": "ジョブID"},
    {"field": "task_name", "headerName": "タスク名"},
]

DOWNLOAD_COLUMNS = [
    "id",
    "status",
    "job_name",
    "data_name",
    "culc_time",
    "total_vehicle_num",
    "total_duration",
]


def layout():
    return html.Div(
        id="archive-id",
        style={"margin-bottom": "30px"},
        children=[
            html.Div(
                "コントロールキーを押しながらクリックすることで複数選択することができます。",
                style={"margin": "12px", "font-size": "16px", "text-align": "left"},
            ),
            dag.AgGrid(
                id="archive-table",
                columnDefs=ARCHIVE_TABLE_COLUMN_DEF,
                dashGridOptions=dict(
                    pagination=True,
                    paginationPageSizeSelector=False,
                    paginationPageSize=ARCHIVE_PAGE_SIZE,
                    animateRows=False,
                    rowSelection="multiple",
                    rowBuffer=0,
                    maxBlocksInCache=1,
                    cacheBlockSize=ARCHIVE_PAGE_SIZE,
                    domLayout="autoHeight",
                ),
                exportDataAsCsv=False,
                csvExportParams=dict(
                    fileName="archive.csv",
                    onlySelected=True,
                    onlySelectedAllPages=True,
                    columnKeys=DOWNLOAD_COLUMNS,
                ),
                rowClassRules={"hidden": "!params.data"},
                rowModelType="infinite",
                defaultColDef=dict(
                    resizable=True,
                    filter=True,
                    sortable=True,
                    wrapText=True,
                    floatingFilter=True,
                ),
                persistence=True,
                persisted_props=["columnState", "selectedRows", "filterModel"],
                persistence_type="session",
            ),
            html.Div(
                id="archive-delete-url",
                children=[
                    dbc.Button(
                        children="削除", id="archive-delete-button", color="danger"
                    ),
                    dbc.Button(
                        children="ダウンロード",
                        id="archive-download-button",
                        color="success",
                        style={"margin-left": 10},
                    ),
                ],
            ),
            html.P(id="archive-delete-message"),
            dcc.Interval(
                id="interval",
                interval=ARCHIVE_PAGE_INTERVAL_SECONDS * 1000,
                n_intervals=0,
            ),
        ],
    )


def _get_archive_data(start_row_idx, end_row_idx, sort_model, filter_model):
    """履歴テーブルのデータを取得する"""
    list_snapshot_id = snap.snapshot_list()
    idx_map_snapshot_id = {i: s for i, s in enumerate(list_snapshot_id, start=1)}

    if filter_model or sort_model:
        list_target_idx = list(idx_map_snapshot_id.keys())
    else:
        list_target_idx = list(idx_map_snapshot_id.keys())[start_row_idx:end_row_idx]

    data = []
    for idx in list_target_idx:
        snapshot_id = idx_map_snapshot_id[idx]

        row = {}
        for col in ARCHIVE_TABLE_COLUMN_DEF:
            cell = snap.meta_get(snapshot_id, col["field"], "")

            if col["field"] == "snapshot_id":
                error_msg = snap.meta_get(snapshot_id, "error", "")

                if len(error_msg) > 0:
                    cell = "[{}]({})".format(
                        "失敗",
                        app.get_relative_path("/{}".format(snapshot_id)),
                    )
                else:
                    task_start_time = snap.meta_get(
                        snapshot_id, "task_start_time", None
                    )
                    task_finish_time = snap.meta_get(
                        snapshot_id, "task_finish_time", None
                    )
                    pdf_status = snap.get_blob(snapshot_id, "pdf")
                    if task_finish_time != "-":
                        if pdf_status:
                            cell = "[{}]({})".format(
                                "成功",
                                app.get_relative_path("/{}.pdf".format(snapshot_id)),
                            )
                        else:
                            cell = "[{}]({})".format(
                                "成功", app.get_relative_path("/{}".format(snapshot_id))
                            )
                    else:
                        if task_start_time != "-":
                            cell = "計算中"
                        else:
                            cell = "待機中"

            elif col["field"] == "id":
                cell = idx

            elif col["field"] == "job-id":
                cell = snapshot_id

            row[col["field"]] = cell
        data.append(row)

    df_archive = pd.DataFrame(data=data)
    # sort data
    if sort_model:
        df_archive = _sort_archive_data(df_archive=df_archive, sort_model=sort_model)

    # filter data
    if filter_model:
        df_archive = _filter_archive_data(
            df_archive=df_archive, filter_model=filter_model
        )
    if sort_model or filter_model:
        nb_total_row = df_archive.shape[0]
        df_archive = df_archive.iloc[start_row_idx:end_row_idx]
    else:
        nb_total_row = len(list_snapshot_id)

    return df_archive, nb_total_row


def _filter_by_condition(df_archive, col_name, filter_type, filter_value):
    """指定されたfilter typeによって履歴テーブルをフィルターする
    指定された列を文字列型にして対応する
    """
    df_filter = df_archive.copy()
    df_filter[col_name] = df_filter[col_name].astype(str)
    if filter_type == "contains":
        df_filter = df_filter[df_filter[col_name].str.contains(filter_value, na=False)]
    elif filter_type == "notContains":
        df_filter = df_filter[~df_filter[col_name].str.contains(filter_value, na=False)]
    elif filter_type == "equals":
        df_filter = df_filter[df_filter[col_name] == filter_value]
    elif filter_type == "notEqual":
        df_filter = df_filter[df_filter[col_name] != filter_value]
    elif filter_type == "startsWith":
        df_filter = df_filter[
            df_filter[col_name].str.startswith(filter_value, na=False)
        ]
    elif filter_type == "endsWith":
        df_filter = df_filter[df_filter[col_name].str.endswith(filter_value, na=False)]
    elif filter_type == "blank":
        df_filter[col_name] = df_filter[col_name].replace(
            ["NaN", "None", ""], float("nan")
        )
        df_filter = df_filter[df_filter[col_name].isnull()]
    elif filter_type == "notBlank":
        df_filter[col_name] = df_filter[col_name].replace(
            ["NaN", "None", ""], float("nan")
        )
        df_filter = df_filter[df_filter[col_name].notnull()]

    return df_filter


def _sort_archive_data(df_archive, sort_model):
    """dataframeをソートして返す"""
    target_cols = [col["colId"] for col in sort_model]
    df_sort = df_archive.copy()
    for c in target_cols:
        df_sort[c] = df_sort[c].astype(str)
        df_sort[c] = df_sort[c].replace(["NaN", "None", ""], float("nan"))
    df_sort = df_sort.sort_values(
        target_cols,
        ascending=[col["sort"] == "asc" for col in sort_model],
        na_position="last",
    )
    return df_sort


def _filter_archive_data(df_archive, filter_model):
    """dataframeをフィルターして返す"""
    for col_name, condition in filter_model.items():
        operator = condition.get("operator", None)
        if operator:
            filter_type1 = condition["condition1"]["type"]
            filter_value1 = condition["condition1"].get("filter", None)
            filter_type2 = condition["condition2"]["type"]
            filter_value2 = condition["condition2"].get("filter", None)
        else:
            filter_type = condition["type"]
            filter_value = condition.get("filter", None)

        if operator == "AND":
            df_archive = _filter_by_condition(
                df_archive=df_archive,
                col_name=col_name,
                filter_type=filter_type1,
                filter_value=filter_value1,
            )
            df_archive = _filter_by_condition(
                df_archive=df_archive,
                col_name=col_name,
                filter_type=filter_type2,
                filter_value=filter_value2,
            )
        elif operator == "OR":
            df1 = _filter_by_condition(
                df_archive=df_archive,
                col_name=col_name,
                filter_type=filter_type1,
                filter_value=filter_value1,
            )
            df2 = _filter_by_condition(
                df_archive=df_archive,
                col_name=col_name,
                filter_type=filter_type2,
                filter_value=filter_value2,
            )
            df_archive = pd.concat([df1, df2], axis=0).drop_duplicates(keep="first")
        else:
            df_archive = _filter_by_condition(
                df_archive=df_archive,
                col_name=col_name,
                filter_type=filter_type,
                filter_value=filter_value,
            )
    return df_archive


@app.callback(
    Output("archive-table", "getRowsResponse"),
    Input("archive-table", "getRowsRequest"),
    Input("interval", "n_intervals"),
    prevent_inital_call=True,
)
def update_table(request, n):
    """テーブルを更新する"""
    if not request:
        return dash.no_update
    df_archive, nb_total_row = _get_archive_data(
        start_row_idx=request["startRow"],
        end_row_idx=request["endRow"],
        sort_model=request["sortModel"],
        filter_model=request["filterModel"],
    )
    return {
        "rowData": df_archive.to_dict("records"),
        "rowCount": nb_total_row,
    }


@app.callback(
    [
        Output("archive-delete-url", "children"),
        Output("archive-delete-message", "children"),
    ],
    Input("archive-delete-button", "n_clicks"),
    [
        State("archive-table", "selectedRows"),
    ],
    prevent_inital_call=True,
)
def delete_snapshot(n_clicks, selected_rows):
    """結果削除ボタンのコールバック"""
    if not n_clicks:
        return dash.no_update

    if not selected_rows:
        return "行を選択してください"

    else:
        inspector = snap.celery_instance.control.inspect()
        worker_id_map_active_tasks = inspector.active()
        worker_id_map_reserved_tasks = inspector.reserved()

        snapshot_id_map_celery_id = {}
        for _, tasks in worker_id_map_active_tasks.items():
            for task in tasks:
                celery_id = task["id"]
                snapshot_id = task["kwargs"]["dash_snapshot_context"]["snapshot_id"]
                snapshot_id_map_celery_id[snapshot_id] = celery_id

        for _, tasks in worker_id_map_reserved_tasks.items():
            for task in tasks:
                celery_id = task["id"]
                snapshot_id = task["kwargs"]["dash_snapshot_context"]["snapshot_id"]
                snapshot_id_map_celery_id[snapshot_id] = celery_id

        message = ""
        for row in selected_rows:
            snapshot_id = row["job-id"]
            create_user_name = row["username"]
            delete_user_name = dea.get_username()
            if delete_user_name is None:
                delete_user_name = "Anonymous"
            is_admin = dea.get_user_data().get("is_admin", False)

            if is_admin or delete_user_name == create_user_name:
                pass
            else:
                message += "{}は削除できません。".format(snapshot_id)
                continue

            # delete celery
            if snapshot_id in snapshot_id_map_celery_id:
                celery_id = snapshot_id_map_celery_id[snapshot_id]
                print("delete cellery is called, %s, %s" % (snapshot_id, celery_id))
                snap.celery_instance.control.revoke(
                    celery_id, terminate=True, signal="SIGKILL"
                )
                message += "{0}を停止しました".format(snapshot_id)

            # delete postgres
            snap.snapshot_delete(snapshot_id)

            # delete directory
            snapshot_dir = os.path.join(
                os.environ["DATA_DIR"], "output_data", snapshot_id
            )
            if os.path.exists(snapshot_dir):
                shutil.rmtree(snapshot_dir)
            message += "ID{0}の結果を削除しました".format(snapshot_id)

    return dcc.Location(id="", href=app.get_relative_path("/archive")), message
