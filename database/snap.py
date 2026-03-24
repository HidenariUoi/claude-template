import logging
import os

from flask_caching import Cache

from app import app, snap

cache = Cache(
    app.server, config={"CACHE_TYPE": "redis", "CACHE_REDIS_URL": os.environ.get("REDIS_URL", "")}
)

logger = logging.getLogger(__name__)


def get_snapshot_list():
    """snapshotの一覧を取得する"""
    # DBとの接続にエラーが出てしまうことがあるので、接続できるまでリトライ
    _passed = False
    n_retry = 5  # 再実行回数
    for _ in range(n_retry):
        try:
            list_snapshot_id = snap.snapshot_list()
        except Exception as e:
            logger.warning("snapshot_idの取得に失敗しました")
            logger.warning(e)
            continue
        else:
            logger.debug("get snapshot_list passed")
            _passed = True
            break
    if not _passed:
        message = f"snapshot_idの取得に{n_retry}回失敗しました"
        logger.error(message)
        raise Exception(message)

    return list_snapshot_id


def make_snapshot_id_map_task_id() -> dict[str, str]:
    """snapshot_idをkeyに、celeryで実行中/待機中のタスクのIDを取得する辞書の作成"""
    inspector = snap.celery_instance.control.inspect()
    worker_id_map_active_tasks = inspector.active()
    worker_id_map_reserved_tasks = inspector.reserved()

    snapshot_id_map_celery_id = {}
    for _, tasks in worker_id_map_active_tasks.items():
        for task in tasks:
            task_id = task["id"]
            snapshot_id = task["kwargs"]["dash_snapshot_context"]["snapshot_id"]
            snapshot_id_map_celery_id[snapshot_id] = task_id
    for _, tasks in worker_id_map_reserved_tasks.items():
        for task in tasks:
            task_id = task["id"]
            snapshot_id = task["kwargs"]["dash_snapshot_context"]["snapshot_id"]
            snapshot_id_map_celery_id[snapshot_id] = task_id

    return snapshot_id_map_celery_id


def delete_snapshot(snapshot_id, dict_snapshot_id_map_task_id):
    # 削除処理
    # celery
    task_id = dict_snapshot_id_map_task_id.get(snapshot_id, None)
    if task_id is not None:
        snap.celery_instance.control.revoke(task_id, terminate=True, signal="SIGKILL")

    # delete postgres
    snap.snapshot_delete(snapshot_id)
    return True
