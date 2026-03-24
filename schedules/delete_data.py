"""スケジュールタスクモジュール"""

import logging
import os
import shutil
import traceback
from io import StringIO

import dash_snapshots.constants as constants
from celery.signals import after_setup_task_logger
from celery.utils.log import get_task_logger
from tenacity import after_log, before_log, retry, stop_after_attempt, wait_exponential

from app import (
    ARCHIVE_PAGE_DELETE_SCHEDULER,
    ARCHIVE_PAGE_REMAIN_NUM,
    CELERY_TASK_NAME_DELETE_ARCHIVE,
    UPLOAD_TMP_DIR,
    snap,
)

logger = get_task_logger(__name__)


@after_setup_task_logger.connect
def setup_task_logger(**kwargs):
    logger = get_task_logger(__name__)
    logger.handlers = []
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)


@snap.celery_instance.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """タスクを設定する関数"""
    sender.add_periodic_task(
        ARCHIVE_PAGE_DELETE_SCHEDULER,
        snap.snapshot_save_periodic(delete_saved_data),
        name="delete saved data every Friday at 22:00",
    )


@snap.celery_instance.task(bind=True, name=CELERY_TASK_NAME_DELETE_ARCHIVE)
@snap.snapshot_async_wrapper(pdf_ssl_verify=False)
def delete_saved_data(self):
    """アプリに保存されたデータを削除するタスク"""
    if self.request.kwargs.get(constants.SNAPSHOT_CONTEXT):
        context = self.request.kwargs.pop(constants.SNAPSHOT_CONTEXT)
        print(f"context = {context}")
        snapshot_id = context.get("snapshot_id", None)
    else:
        raise Exception("could not get snapshot_id")

    try:
        nb_snapshot_delete = _delete_snapshot_database_and_dirs()
    except Exception:
        e = traceback.format_exc()
        logger.error("過去履歴の削除に失敗しました。%s" % e)
    finally:
        logger.info("%d 件のスナップショットの削除に成功しました。" % nb_snapshot_delete)

    try:
        nb_upload_delete = _delete_upload_dirs()
    except Exception:
        e = traceback.format_exc()
        logger.error("アップロードフォルダの削除に失敗しました。%s" % e)
    finally:
        logger.info("%d 件のアップロードフォルダの削除に成功しました。" % nb_upload_delete)

    snap.meta_update(
        snapshot_id,
        dict(
            nb_snapshot_delete=nb_snapshot_delete,
            nb_upload_delete=nb_upload_delete,
            task_name=CELERY_TASK_NAME_DELETE_ARCHIVE,
            job_name="[定期]過去履歴削除",
        ),
    )

    return True


@retry(
    wait=wait_exponential(multiplier=1, min=3, max=40),
    stop=stop_after_attempt(3),
    before=before_log(logger, logging.INFO),
    after=after_log(logger, logging.INFO),
)
def _delete_snapshot_database_and_dirs():
    """snapshotの履歴を削除する"""
    logger.info("start delete snapshots")
    list_snapshot_id = snap.snapshot_list()
    # お気に入りを優先的に保存
    remain_snapshot_id = []
    for snapshot_id in list_snapshot_id:
        if snap.meta_get(snapshot_id, "star", False):
            remain_snapshot_id.append(snapshot_id)
    # 残りの保存枠に割り当てる
    for snapshot_id in list_snapshot_id:
        if len(remain_snapshot_id) >= ARCHIVE_PAGE_REMAIN_NUM:
            break
        if snapshot_id in remain_snapshot_id:
            continue
        remain_snapshot_id.append(snapshot_id)
    # 削除するsnapshot_idを決定
    delete_snapshot_id = list(set(list_snapshot_id) - set(remain_snapshot_id))
    print("delete snapshot id num %d" % len(delete_snapshot_id))

    nb_delete = 0
    snapshot_table = snap.store.Snapshot.__table__
    for snapshot_id in delete_snapshot_id:
        try:
            with snap.store.db.engine.begin() as conn:
                # delete snapshot database record
                sql_query = snapshot_table.delete(snapshot_table.c.id == snapshot_id)
                conn.execute(sql_query)

                # delete snapshot directory
                snapshot_dir_path = os.path.join(os.environ["DATA_DIR"], "output_data", snapshot_id)
                if os.path.exists(snapshot_dir_path):
                    shutil.rmtree(snapshot_dir_path)
                logger.info(str(snapshot_id) + "deleted")
                nb_delete += 1
        except Exception:
            e = traceback.format_exc()
            logger.error("%s snapshot delete failed %s" % (snapshot_id, e))

    return nb_delete


def _delete_upload_dirs():
    """アップロードフォルダの中身を削除する"""
    list_uploaded_file_dir = os.listdir(UPLOAD_TMP_DIR)

    nb_delete = 0
    for dir_name in list_uploaded_file_dir:
        try:
            shutil.rmtree(os.path.join(UPLOAD_TMP_DIR, dir_name))
            nb_delete += 1
        except Exception:
            e = traceback.format_exc()
            logger.error("%s upload delete failed %s" % (dir_name, e))

    return nb_delete
