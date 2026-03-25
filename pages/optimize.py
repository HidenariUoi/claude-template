"""最適化実行画面
"""
import pandas as pd
import os
import traceback

import datetime as dt
import dash_design_kit as ddk
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
import dash_uploader as du
import dash_snapshots.constants as constants
import numpy as np
from dash.dependencies import Input, Output, State
import dash
from dash import html, dcc, callback_context, no_update
from flask_caching import Cache
from database.auth.auth_schema import get_theme_and_sub_theme_name

from app import app, snap, CELERY_TASK_NAME_OPTIMIZE, UPLOAD_TMP_DIR

import dash_snapshots.constants as constants

from scripts.run_optimize import main as optimize_main
from app import snap, CELERY_TASK_NAME_OPTIMIZE



def layout(data_name):
    """最適化実行ページを作成する
    :return:
    """
    return ddk.Card([
        dcc.Store(id="register-data-name", data=data_name),
        html.Div(id="optimize-upload-error"),
        du.Upload(
            id="register-mst-file-uploader",
            text="入力データをアップロードしてください",
            filetypes=["xlsx", "xls"],
            max_files=1,
            default_style={
                "height": "130px",
                "border-width": "1px",
                "border-style": "dashed",
                "border-radius": "5px",
                "text-align": "center",
                "margin": "16px",
                "font-size": "15px",
            },
        ),
        dbc.Input(
            id="optimize-job-name",
            placeholder="ジョブ名を入力してください",
            type="text",
            style={"margin": "16px"},
        ),
        html.Button(
            "最適化実行",
            id="optimize-run-button",
            disabled=True,
            style={"margin": "16px"},
        ),
        html.Div(id="optimize-run-output"),
    ])


@app.callback(
    Output("optimize-run-button", "disabled"),
    Input("optimize-job-name", "value"),
    Input("register-mst-file-uploader", "isCompleted"),
    Input("optimize-upload-error", "children"),
)
def toggle_run_button(job_name, is_completed, upload_error):
    """バリデーションが通っている場合のみボタンを有効化する"""
    if job_name and is_completed and not upload_error:
        return False
    return True


@app.callback(
    Output("optimize-upload-error", "children"),
    Input("register-mst-file-uploader", "isCompleted"),
    State("register-mst-file-uploader", "fileNames"),
    State("register-mst-file-uploader", "upload_id"),
    prevent_initial_call=True,
)
def show_upload_error(is_completed, file_names, upload_id):
    """アップロード完了時にファイルの検証を行い、エラーがあれば表示する"""
    if not is_completed or not file_names:
        return None

    file_path = os.path.join(UPLOAD_TMP_DIR, upload_id, file_names[0])

    try:
        pd.read_excel(file_path)
        return None
    except Exception as e:
        return dbc.Alert(
            [
                html.Strong("ファイルの読み込みエラー: "),
                html.Pre(traceback.format_exc(), style={"white-space": "pre-wrap", "margin-top": "8px"}),
            ],
            color="danger",
            style={"margin": "16px"},
        )


@app.callback(
    Output("url", "pathname", allow_duplicate=True),
    Input("optimize-run-button", "n_clicks"),
    State("optimize-job-name", "value"),
    State("register-mst-file-uploader", "isCompleted"),
    State("register-mst-file-uploader", "fileNames"),
    State("register-mst-file-uploader", "upload_id"),
    State("register-data-name", "data"),
    prevent_initial_call=True,
)
def run_optimize(n_clicks, job_name, is_completed, file_names, upload_id, data_name):
    """最適化実行ボタンのコールバック"""
    if not n_clicks:
        return no_update
    snapshot_id = snap.snapshot_save_async(
        run_optimize_task,
        job_name=job_name,
    )
    snap.meta_update(
        snapshot_id,
        dict(
            job_name=job_name,
            data_name=data_name,
            data_name_ja=get_theme_and_sub_theme_name(data_name),
            task_name=CELERY_TASK_NAME_OPTIMIZE,
        )
    )
    return app.get_relative_path("/archive")


@snap.celery_instance.task(bind=True, name=CELERY_TASK_NAME_OPTIMIZE)
@snap.snapshot_async_wrapper()
def run_optimize_task(self, job_name):
    """ジョブの実行関数、結果をJSON形式でpostgresに保存する"""
    context = self.request.kwargs.pop(constants.SNAPSHOT_CONTEXT)
    snapshot_id = context.get("snapshot_id", None)

    save_dir = os.path.join(os.environ["DATA_DIR"], "output_data", snapshot_id)
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # run main
    try:
        main_output = optimize_main()
    except Exception as e:
        full_error = traceback.format_exc()
        snap.meta_update(snapshot_id, {"full_error": full_error})

    return True
