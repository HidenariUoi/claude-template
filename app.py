import datetime
import os
from multiprocessing.util import register_after_fork

import dash_snapshots
import dash_uploader as du
import plotly.colors as plotly_colors
from celery.schedules import crontab
from dash_enterprise_libraries import EnterpriseDash
from sqlalchemy import create_engine, event, exc, select, text


app = EnterpriseDash(
    __name__,
    suppress_callback_exceptions=True,
    title="最適化テンプレート",
)
app.setup_shortcuts(
    size="slim",
)

snap = dash_snapshots.DashSnapshots(app, database_url=os.environ["DATABASE_URL"])
engine = create_engine(
    os.environ["DATABASE_URL"],
    echo=False,
    pool_pre_ping=True,
)

# URL
SPECIFICATION_URL = app.get_relative_path("/assets/仕様書.pdf")
TABLE_DEFINITION_URL = app.get_relative_path("/assets/サンプルデータ.csv")


# 日付のフォーマット
DATE_FORMAT = "%Y/%m/%d"
TIME_FORMAT = "%H:%M"

INPUT_DATA_DIR = os.path.join(os.environ["DATA_DIR"], "input_data")
UPLOAD_TMP_DIR = os.path.join(os.environ["DATA_DIR"], "upload")
OUTPUT_DATA_DIR = os.path.join(os.environ["DATA_DIR"], "output_data")
if not os.path.exists(INPUT_DATA_DIR):
    os.makedirs(INPUT_DATA_DIR)
if not os.path.exists(UPLOAD_TMP_DIR):
    os.makedirs(UPLOAD_TMP_DIR)
if not os.path.exists(OUTPUT_DATA_DIR):
    os.makedirs(OUTPUT_DATA_DIR)

# アップロード先の一時ディレクトリ
du.configure_upload(app, UPLOAD_TMP_DIR)

# encodingの指定
FILE_ENCODING = "cp932"

# csvファイルのencodingの設定
CSV_FILE_ENCODING = "utf-8-sig"

# 履歴ページのお気に入り件数上限
ARCHIVE_STAR_SIZE = 50

# 履歴ページの更新頻度
ARCHIVE_PAGE_INTERVAL_SECONDS = 30

# 履歴ページの１ページ当たりの表示件数
ARCHIVE_PAGE_SIZE = 10

# 履歴ページで定期削除の際に、残す件数
ARCHIVE_PAGE_REMAIN_NUM = 300

# 履歴ページを削除するタイミング
ARCHIVE_PAGE_DELETE_SCHEDULER = crontab(hour=22, minute=0, day_of_week="5", day_of_month="*")

# 非同期タスクのジョブ名
CELERY_TASK_NAME_OPTIMIZE = "最適化"
CELERY_TASK_NAME_DELETE_ARCHIVE = "履歴削除"

# モデルで利用する最大CPU数
MAX_MODEL_CPU = os.environ.get("MAX_MODEL_CPU", 4)

def dispose_engine(engine):
    """dispose SqlAlchemy engine in register_after_fork"""
    engine.dispose()


with app.server.app_context():
    register_after_fork(snap.store.db.engine, dispose_engine)


@event.listens_for(snap.store.db.engine, "engine_connect")
def ping_connection(connection, branch):
    try:
        # run a SELECT 1.   use a core select() so that
        # the SELECT of a scalar value without a table is
        # appropriately formatted for the backend
        connection.scalar(select(1))
    except exc.DBAPIError as err:
        # catch SQLAlchemy's DBAPIError, which is a wrapper
        # for the DBAPI's exception.  It includes a .connection_invalidated
        # attribute which specifies if this connection is a "disconnect"
        # condition, which is based on inspection of the original exception
        # by the dialect in use.
        if err.connection_invalidated:
            # run the same SELECT again - the connection will re-validate
            # itself and establish a new connection.  The disconnect detection
            # here also causes the whole connection pool to be invalidated
            # so that all stale connections are discarded.
            connection.scalar(select(1))
        else:
            raise
