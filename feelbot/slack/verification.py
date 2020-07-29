import hashlib
import hmac
import os
import time

from fastapi import Header, Request, HTTPException
from loguru import logger


async def verify_signature(
    request: Request,
    x_slack_signature: str = Header(...),
    x_slack_request_timestamp: str = Header(...),
) -> None:
    # https://api.slack.com/authentication/verifying-requests-from-slack
    logger.debug("verification start")

    body = await request.body()
    sig_basestring = str.encode('v0:' + x_slack_request_timestamp + ':') + body
    my_hash = hmac.new(
        os.environ.get("SLACK_SIGNING_SECRET").encode(),
        sig_basestring,
        hashlib.sha256
    ).hexdigest()
    my_signature = f'v0={my_hash}'

    if not hmac.compare_digest(x_slack_signature, my_signature):
        logger.info('slack verification failed')
        raise HTTPException(status_code=403, detail="Forbidden")

    logger.debug("verification successful")


async def verify_timestamp(
    x_slack_request_timestamp: str = Header(...)
) -> None:
    # https://api.slack.com/authentication/verifying-requests-from-slack
    timeout = 60 * 5
    request_timeout_time = int(x_slack_request_timestamp) + timeout
    current_time = time.time()

    if request_timeout_time < current_time:
        logger.info("slack request timestamp reached timeout")
        raise HTTPException(status_code=403, detail="Forbidden")
