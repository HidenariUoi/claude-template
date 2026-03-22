"""最適化ジョブのタスク
"""
from app import CELERY_TASK_NAME_MODEL


@snap.celery_instance.task(bind=True, name=CELERY_TASK_NAME_MODEL)
@snap.snapshot_async_wrapper()
def run_model(
    self,
    target_date,
    culc_time,
):
    """ジョブの実行関数、結果をJSON形式でpostgresに保存する"""
    pass
