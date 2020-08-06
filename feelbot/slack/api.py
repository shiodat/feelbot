import json
import os
from threading import Thread

import requests
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from loguru import logger

from .verification import verify_signature, verify_timestamp
from .models import SlackCommand
from ..client import Client
from ..utils import convert_datetime

app = FastAPI()
load_dotenv(verbose=True)


@app.post(
    '/find',
    response_model=str,
    dependencies=[Depends(verify_signature), Depends(verify_timestamp)]
)
async def find_lesson(request: Request):
    form = await request.form()
    command = SlackCommand(**form)
    if command.command != '/find':
        raise ValueError('endpoint does not match')
    studio, schedule, polling = _parse_parameters(command.text.split())
    thread = Thread(
        target=_background_find_lesson,
        args=[command.user_id, studio, schedule, polling],
        daemon=True
    )
    thread.start()
    if polling:
        return 'notify when the lesson can be reserved, please wait'
    else:
        return 'finding...'


def _background_find_lesson(
    user_id, studio, schedule, polling=False, sleep=30
):
    with Client() as client:
        try:
            lesson = client.find_lesson(
                studio, schedule, polling=polling, sleep=sleep)
            incoming_webhook(user_id,
                             lesson.text(prefix='lesson information\n'))
        except Exception as e:
            logger.exception(f'{e}')
            logger.exception(user_id,
                             f'something wrong: {e.__class__.__name__}\n{e}')


@app.post(
    '/reserve',
    response_model=str,
    dependencies=[Depends(verify_signature), Depends(verify_timestamp)]
)
async def reserve_lesson(request: Request):
    form = await request.form()
    command = SlackCommand(**form)
    if command.command != '/reserve':
        raise ValueError('endpoint does not match')
    studio, schedule, polling = _parse_parameters(command.text.split())
    thread = Thread(
        target=_background_reserve_lesson,
        args=[command.user_id, studio, schedule, polling, True],
        daemon=True
    )
    thread.start()
    if polling:
        return 'reserve the lesson when it becomes vacant, please wait'
    else:
        return 'reserving...'


@app.post(
    '/relocate',
    response_model=str,
    dependencies=[Depends(verify_signature), Depends(verify_timestamp)]
)
async def relocate_lesson(request: Request):
    form = await request.form()
    command = SlackCommand(**form)
    if command.command != '/relocate':
        raise ValueError('endpoint does not match')
    studio, schedule, polling = _parse_parameters(command.text.split())
    thread = Thread(
        target=_background_reserve_lesson,
        args=[command.user_id, studio, schedule, polling, True],
        daemon=True
    )
    thread.start()
    if polling:
        return 'relocate the lesson when it becomes vacant, please wait'
    else:
        return 'relocating...'


def _background_reserve_lesson(
    user_id, studio, schedule, relocate=False, polling=False, sleep=30
):
    with Client() as client:
        try:
            success, lesson = client.reserve_lesson(
                studio, schedule, relocate=relocate,
                polling=polling, sleep=sleep)
            pref = 'reservation success!\n' if success else 'reservation failed\n'
            incoming_webhook(user_id, lesson.text(prefix=pref))
        except Exception as e:
            logger.exception(f'{e}')
            incoming_webhook(user_id,
                             f'something wrong: {e.__class__.__name__}\n{e}')


def _parse_parameters(parameters):
    if len(parameters) == 3:
        studio, date, start_time = parameters
        polling = False
    elif len(parameters) == 4:
        studio, date, start_time, polling = parameters
        polling = True if polling == 'auto' else False
    else:
        raise ValueError('invalid parameters')
    schedule = convert_datetime(date, start_time)
    return studio, schedule, polling


def incoming_webhook(user_id, message):
    message = f'<@{user_id}> ' + message
    logger.info('webhook response\n' + message)
    requests.post(
        os.environ.get('FEELCYCLE_BOT_INCOMING_WEBHOOK'),
        data=json.dumps({'text': message}).encode('utf-8'))
