import logging
import os
from typing import Generator

import dash
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import dash_daq as daq
import dash_enterprise_auth as dea
import pandas as pd
from dash import html
from dash_enterprise_libraries import ddk

from app import (
    ARCHIVE_PAGE_SIZE,
    ARCHIVE_STAR_SIZE,
    app,
    snap,
    CELERY_TASK_NAME_DELETE_ARCHIVE
)
from database.auth.auth_schema import get_theme_and_sub_theme_name, get_list_accessable_data_info
from database.snap import get_snapshot_list, make_snapshot_id_map_task_id
from utils import parse_log_file

logger = logging.getLogger(__name__)

ARCHIVE_TABLE_COLUMN_DEF = [
    {
        "field": "id",
        "headerName": "id",
        "width": "100",
        "filter": "agNumberColumnFilter",
        "floatingFilter": False,
        "suppressMenu": True,
        "floatingFilterComponentParams": {
            "suppressFilterButton": True,
        },
    },
    {
        "field": "star",
        "headerName": "お気に入り",
        "width": "120",
        "floatingFilter": False,
        "suppressMenu": True,
    },
    {
        "field": "status",
        "headerName": "ステータス",
        "cellRenderer": "markdown",
        "filter": "agTextColumnFilter",
        "floatingFilter": True,
        "suppressMenu": True,
        "floatingFilterComponentParams": {
            "suppressFilterButton": True,
        },
    },
    {
        "field": "theme_name",
        "headerName": "テーマ名",
        "filter": "agTextColumnFilter",
        "floatingFilter": True,
        "suppressMenu": True,
        "floatingFilterComponentParams": {
            "suppressFilterButton": True,
        },
    },
    {
        "field": "sub_theme_name",
        "headerName": "サブテーマ名",
        "filter": "agTextColumnFilter",
        "floatingFilter": True,
        "suppressMenu": True,
        "floatingFilterComponentParams": {
            "suppressFilterButton": True,
        },
    },
    {
        "field": "job_name",
        "headerName": "ジョブ名",
        "filter": "agTextColumnFilter",
        "floatingFilter": True,
        "suppressMenu": True,
        "floatingFilterComponentParams": {
            "suppressFilterButton": True,
        },
    },
    {
        "field": "task_name",
        "headerName": "タスク名",
        "filter": "agTextColumnFilter",
        "floatingFilter": True,
        "suppressMenu": True,
        "floatingFilterComponentParams": {
            "suppressFilterButton": True,
        },
    },
    {
        "field": "error",
        "headerName": "エラーメッセージ",
        "filter": "agTextColumnFilter",
        "floatingFilter": True,
        "suppressMenu": True,
        "floatingFilterComponentParams": {
            "suppressFilterButton": True,
        },
    },
    {
        "field": "created_time",
        "headerName": "実行日付",
        "filter": "agTextColumnFilter",
        "floatingFilter": True,
        "suppressMenu": True,
        "floatingFilterComponentParams": {
            "suppressFilterButton": True,
        },
    },
    {
        "field": "username",
        "headerName": "実行者",
        "filter": "agTextColumnFilter",
        "floatingFilter": True,
        "suppressMenu": True,
        "floatingFilterComponentParams": {
            "suppressFilterButton": True,
        },
    },
    {
        "field": "job-id",
        "headerName": "ジョブID",
        "filter": "agTextColumnFilter",
        "floatingFilter": True,
        "suppressMenu": True,
        "floatingFilterComponentParams": {
            "suppressFilterButton": True,
        },
    },
]

DOWNLOAD_COLUMNS = [
    "id",
    "status",
    "job_name",
    "data_name",
]
_n_star_message = "お気に入り: {n_stars}件 / 最大" + f"{ARCHIVE_STAR_SIZE}件"


############################
# layouts
############################


def get_boolean_switch_layout(
    page_name,
    star_id,
    star_on,
    owner_id,
    owner_on,
    sub_theme_id=None,
    sub_theme_on=False,
    sub_theme_name=None,
):
    children = [
        ddk.ControlItem(
            daq.BooleanSwitch(
                id=star_id,
                on=star_on,
                label="お気に入りのみ",
                labelPosition="right",
                color="#CCCCCC",
            ),
            height=30,
        ),
        ddk.ControlItem(
            daq.BooleanSwitch(
                id=owner_id,
                on=owner_on,
                label="自分のみ",
                labelPosition="right",
                color="#CCCCCC",
            ),
            height=30,
        ),
    ]
    if page_name == "archive":
        children.append(
            ddk.ControlItem(
                daq.BooleanSwitch(
                    id=sub_theme_id,
                    on=sub_theme_on,
                    label=f"{sub_theme_name}のみ",
                    labelPosition="right",
                    color="#CCCCCC",
                ),
                height=30,
            )
        )
    return html.Div(children=children)


def get_archive_table_layout(page_name, aggrid_id, rowData):
    if page_name == "archive":
        col_def = [col for col in ARCHIVE_TABLE_COLUMN_DEF if col["field"] != "theme_name"]
    else:
        col_def = ARCHIVE_TABLE_COLUMN_DEF
    return dag.AgGrid(
        id=aggrid_id,
        columnDefs=col_def,
        enableEnterpriseModules=True,
        licenseKey=os.environ.get("AG_LICENSE_KEY", ""),
        dashGridOptions=dict(
            pagination=True,
            paginationPageSizeSelector=False,
            paginationPageSize=ARCHIVE_PAGE_SIZE,
            animateRows=False,
            rowSelection="multiple",
            rowBuffer=0,
            maxBlocksInCache=1,
            cacheBlockSize=ARCHIVE_PAGE_SIZE,
            # domLayout="autoHeight",
        ),
        exportDataAsCsv=False,
        csvExportParams={
            "columnKeys": DOWNLOAD_COLUMNS,
            "fileName": "archive.csv",
            "onlySelected": True,
            "onlySelectedAllPages": True,
        },
        rowClassRules={"hidden": "!params.data"},
        rowModelType="clientSide",
        defaultColDef=dict(
            resizable=True,
            filter=True,
            sortable=True,
            wrapText=True,
            floatingFilter=True,
        ),
        persistence=True,
        persisted_props=["columnState", "selectedRows", "filterModel"],
        persistence_type="memory",
        dangerously_allow_code=True,
        rowData=rowData,
    )


def get_archive_delete_layout(delete_url_id, delete_button_id, download_button_id, message_id):
    return html.Div(
        children=[
            html.Div(
                id=delete_url_id,
                children=[
                    html.Button(
                        children="削除", 
                        id=delete_button_id, 
                        style={
                            "backgroundColor": "#dc3545",
                            "border": "2px solid #dc3545",
                        },
                    ),
                    html.Button(
                        children="ダウンロード",
                        id=download_button_id,
                        style={
                            "backgroundColor": "green",
                            "border": "2px solid green",
                            "margin-left": 10
                        },
                    ),
                ],
            ),
            html.P(id=message_id),
        ]
    )


def get_n_stars(data_name):
    """お気に入り指定数の計算. data_nameが一致するsnapshotのみが集計対象"""
    n_stars = 0
    for snapshot_id in _filtered_snapshot_id_iter(
        data_name,
        filter_by_star=False,
        filter_by_owner=False,
        filter_by_sub_theme=False,
    ):
        if snap.meta_get(snapshot_id, "star", False):
            n_stars += 1
    return n_stars


def get_archive_data_star_num(
    page_name: str,
    data_name: str = None,
    star_on: bool = False,
    owner_on: bool = False,
    sub_theme_on: bool = False,
) -> tuple[pd.DataFrame, int]:
    """履歴テーブルのデータを取得する"""

    # 表示範囲のsnapshot_idに紐づく情報を取得
    data = []
    n_stars = 0
    for idx, snapshot_id in enumerate(
        _filtered_snapshot_id_iter(page_name, data_name, star_on, owner_on, sub_theme_on),
        start=1,
    ):
        if snap.meta_get(snapshot_id, "star", False):
            n_stars += 1

        row = {}
        for col in ARCHIVE_TABLE_COLUMN_DEF:
            cell = snap.meta_get(snapshot_id, col["field"], "")

            if col["field"] == "status":
                cell = _format_job_status(snapshot_id)
            if col["field"] == "id":
                cell = idx
            elif col["field"] == "job-id":
                cell = snapshot_id
            elif col["field"] == "star":
                cell = "★" if cell else "☆"
            elif col["field"] == "theme_name" and page_name == "all_snapshot":
                data_name = snap.meta_get(snapshot_id, "data_name", "")
                theme_name, _ = get_theme_and_sub_theme_name(data_name)
                cell = theme_name if theme_name else ""
            elif col["field"] == "sub_theme_name":
                data_name = snap.meta_get(snapshot_id, "data_name", "")
                _, sub_theme_name = get_theme_and_sub_theme_name(data_name)
                cell = sub_theme_name if sub_theme_name else ""

            row[col["field"]] = cell
        data.append(row)

    df_archive = pd.DataFrame(data=data)

    return df_archive, n_stars


def _filtered_snapshot_id_iter(
    page_name: str,
    data_name: str = None,
    filter_by_star: bool = False,
    filter_by_owner: bool = False,
    filter_by_sub_theme: bool = False,
) -> Generator[str, None, None]:
    list_snapshot_id = get_snapshot_list()

    username = dea.get_username()
    list_accessable_data_name = [
        data.hashed_data_name for data in get_list_accessable_data_info(username)
    ]

    if page_name == "archive":
        theme_name, sub_theme_name = get_theme_and_sub_theme_name(data_name)

    for snapshot_id in list_snapshot_id:
        # 共通の条件
        if filter_by_star and snap.meta_get(snapshot_id, "star", False) is False:
            continue
        if filter_by_owner and snap.meta_get(snapshot_id, "username", "") != username:
            continue

        task_name = snap.meta_get(snapshot_id, "task_name", "")
        if task_name == CELERY_TASK_NAME_DELETE_ARCHIVE:
            yield snapshot_id

        if page_name == "archive":
            snapshot_data_name = snap.meta_get(snapshot_id, "data_name", "")
            if (
                list_accessable_data_name is not None
                and snapshot_data_name not in list_accessable_data_name
            ):
                continue
            if snapshot_data_name == "":
                continue
            snapshot_theme_name, snapshot_sub_theme_name = get_theme_and_sub_theme_name(snapshot_data_name)
            if snapshot_theme_name != theme_name:
                continue
            if filter_by_sub_theme and snapshot_sub_theme_name != sub_theme_name:
                continue
        else:
            data_name = snap.meta_get(snapshot_id, "data_name", "")
            if data_name not in list_accessable_data_name:
                continue

        yield snapshot_id
    return


def _format_job_status(snapshot_id):
    """
    失敗：エラーメッセージがある
    成功：タスクが終了していてかつエラーメッセージがない
    待機中：タスクが開始していない
    前処理中：タスクが開始していてLocalSolverのログが存在しない
    計算中(○○%)：タスクが開始していてLocalSolverのログが存在し、合計計算時間が設定した計算時間に満たない
    後処理中：タスクが開始していてLocalSolverのログが存在し、合計計算時間が設定した計算時間と一致する
    """
    error_msg = snap.meta_get(snapshot_id, "error", "")
    if len(error_msg) > 0:
        cell = "<a href='{}' target='_blank' rel='noopener'>{}</a>".format(
            app.get_relative_path("/{}".format(snapshot_id)),
            "失敗",
        )
    else:
        task_start_time = snap.meta_get(snapshot_id, "task_start_time", None)
        task_finish_time = snap.meta_get(snapshot_id, "task_finish_time", None)
        if task_finish_time != "-":
            cell = "<a href='{}' target='_blank' rel='noopener'>{}</a>".format(
                app.get_relative_path("/{}".format(snapshot_id)),
                "成功",
            )
        else:
            if task_start_time == "-":
                cell = "待機中"
            else:
                # localsolver.logをパース
                log_path = os.path.join(
                    os.environ["DATA_DIR"],
                    "output_data",
                    snapshot_id,
                    "localsolver.log",
                )
                if not os.path.exists(log_path):
                    cell = "前処理中"
                else:
                    total_culc_seconds = snap.meta_get(snapshot_id, "culc_time", None)
                    obj_priority_dic = snap.meta_get(snapshot_id, "obj_priority_dic")
                    df_result = parse_log_file(log_path, obj_priority_dic)
                    passed_culc_seconds = 0
                    if not df_result.empty:
                        passed_culc_seconds = df_result.iloc[-1]["time"]
                    if passed_culc_seconds == total_culc_seconds:
                        cell = "後処理中"
                    else:
                        progress_rate = int(passed_culc_seconds / total_culc_seconds * 100)

                        cell = f"計算中 ({progress_rate}%)"
    return cell


############################
# callbacks
############################


def update_table(
    page_name,
    star_on,
    owner_on,
    sub_theme_on=False,
    data_name=None,
):
    """intervalのカウントが増えるときやスイッチが押された時に、表示するデータを更新"""
    df_archive, n_stars = get_archive_data_star_num(
        page_name=page_name,
        data_name=data_name,
        star_on=star_on,
        owner_on=owner_on,
        sub_theme_on=sub_theme_on,
    )
    return df_archive.to_dict("records"), _n_star_message.format(n_stars=n_stars)


def set_stars(
    page_name,
    cell,
    data,
    star_on,
    owner_on,
    sub_theme_on: bool = False,
    data_name: str = None,
):
    """星がクリックされた時にsnapshotのデータを更新したうえで、ag-gridのテーブル表示も更新する"""
    if cell["colId"] != "star":
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    n_stars = get_n_stars(data_name)
    star = cell["value"]
    row_idx = cell["rowIndex"]
    snapshot_id = data[row_idx]["job-id"]

    if star == "★":
        snap.meta_update(snapshot_id, {"star": False})
    elif star == "☆":
        if n_stars >= ARCHIVE_STAR_SIZE:
            return (
                True,
                "danger",
                f"お気に入り登録できる履歴は 最大{ARCHIVE_STAR_SIZE}件 です。",
                dash.no_update,
                dash.no_update,
            )
        snap.meta_update(snapshot_id, {"star": True})

    df_archive, n_stars = get_archive_data_star_num(
        page_name=page_name,
        data_name=data_name,
        star_on=star_on,
        owner_on=owner_on,
        sub_theme_on=sub_theme_on,
    )
    return (
        False,
        dash.no_update,
        dash.no_update,
        _n_star_message.format(n_stars=n_stars),
        df_archive.to_dict("records"),
    )


def download_file(n_clicks):
    """ダウンロードに対するコールバック"""
    if n_clicks:
        return True

    return False


def delete_snapshot(
    page_name,
    n_clicks,
    selected_rows,
    star_on=False,
    owner_on=False,
):
    """結果削除のコールバック"""
    if not n_clicks:
        return dash.no_update, dash.no_update

    if not selected_rows:
        return dash.no_update, "行を選択してください"

    dict_snapshot_id_map_task_id = make_snapshot_id_map_task_id()

    # 削除者の情報
    delete_user = dea.get_username()
    delete_user = "Anonymous" if delete_user is None else delete_user
    # TODO: deaではadmin情報は取れないので、cookieから取る
    delete_user_is_admin = dea.get_user_data().get("is_admin", False)

    message = ""
    for row in selected_rows:
        snapshot_id = row["job-id"]

        # 削除の権限があるか判定
        same_creator_and_deleter = row["username"] == delete_user
        able_to_delete = same_creator_and_deleter or delete_user_is_admin
        if not able_to_delete:
            message += "{}は削除できません。".format(snapshot_id)
            continue

        # 削除処理
        # celery
        task_id = dict_snapshot_id_map_task_id.get(snapshot_id, None)
        if task_id is not None:
            # NOTE: loggerにしたい
            print("delete cellery is called, %s, %s" % (snapshot_id, task_id))
            snap.celery_instance.control.revoke(task_id, terminate=True, signal="SIGKILL")
            message += "{0}を停止しました".format(snapshot_id)

        # delete postgres
        snap.snapshot_delete(snapshot_id)
        message += "ID{0}の結果を削除しました".format(snapshot_id)

    if page_name == "archive":
        return app.get_relative_path("/archive"), message
    else:
        df_archive, n_stars = get_archive_data_star_num(
            page_name=page_name,
            star_on=star_on,
            owner_on=owner_on,
        )
        return df_archive.to_dict("records"), message
