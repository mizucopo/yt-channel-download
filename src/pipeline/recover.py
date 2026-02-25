"""中断状態回復パイプライン.

処理が中断されたストリームを回復可能な状態に戻す。
"""

import logging

from src import db
from src.config import settings

logger = logging.getLogger(__name__)


def recover_streams() -> int:
    """中断されたストリームを回復する.

    downloading -> discovered: ダウンロードを再試行
    uploading -> thumbs_done: アップロードを再試行

    Returns:
        回復されたストリーム数
    """
    count = 0

    # downloading状態をdiscoveredに戻す
    downloading_streams = db.get_streams_by_status("downloading")
    for stream in downloading_streams:
        if stream.retry_count >= settings.max_retries:
            continue

        updated = db.update_status(
            stream.video_id,
            "discovered",
            expected_old_status="downloading",
            increment_retry=True,
        )
        if updated:
            logger.info("Recovered stream from downloading: %s", stream.video_id)
            count += 1

    # uploading状態をthumbs_doneに戻す
    uploading_streams = db.get_streams_by_status("uploading")
    for stream in uploading_streams:
        if stream.retry_count >= settings.max_retries:
            continue

        updated = db.update_status(
            stream.video_id,
            "thumbs_done",
            expected_old_status="uploading",
            increment_retry=True,
        )
        if updated:
            logger.info("Recovered stream from uploading: %s", stream.video_id)
            count += 1

    return count
