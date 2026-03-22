"""snapshotページ
"""
import pages.snapshots as snapshots
from app import (
    snap,
    CELERY_TASK_NAME_MODEL,
)


def layout(snapshot_id):
    task_name = snap.meta_get(snapshot_id, "task_name")
    error_msg = snap.meta_get(snapshot_id, "error", "")
    if error_msg:
        return snapshots.error.layout(snapshot_id=snapshot_id)

    if task_name == CELERY_TASK_NAME_MODEL:
        job_name = snap.meta_get(snapshot_id, "job_name")
        return snapshots.model.layout(snapshot_id=snapshot_id, job_name=job_name)
    else:
        raise Exception("invalid task name %s" % task_name)
