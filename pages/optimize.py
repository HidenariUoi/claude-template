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
from app import app



def layout(data_name):
    """最適化実行ページを作成する
    :return:
    """
    return []