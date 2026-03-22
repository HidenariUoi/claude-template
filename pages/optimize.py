"""最適化実行画面
"""
import pandas as pd
import os
import datetime as dt
import dash_design_kit as ddk
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
import dash
import traceback
import dash_snapshots.constants as constants
import numpy as np
from dash.dependencies import Input, Output, State
from dash import html, dcc
from flask_caching import Cache

from scripts.run_optimize import main
from models.make_area_data import make_area_data_from_db
from models.vrp.dataclass import FixRouteData
from models.vrp.make_vrp_data import make_list_fix_route_data
from app import (
    app,
    snap,
    engine,
    DATE_FORMAT,
    CELERY_TASK_NAME_MODEL,
)





def layout():
    """最適化実行ページを作成する
    :return:
    """
    



@app.callback(
    prevent_initial_call=True,
)
def run_job(
    n_clicks,
):
    """ジョブ実行ボタンに対するコールバック"""
    return (
        dcc.Location(id="optimize-location", href=app.get_relative_path("/archive")),
        dash.no_update,
    )


