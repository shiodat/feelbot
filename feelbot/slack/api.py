import json
import os
from datetime import datetime
from threading import Thread
from typing import List

import requests
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from loguru import logger

from .verification import verify_signature, verify_timestamp
from .models import SlackCommand
from ..client import Client
from ..models import lessons2csv
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
    studio, schedule, polling, sleep = _parse_parameters(command.text.split())
    thread = Thread(
        target=_background_find_lesson,
        args=[command.user_id, studio, schedule, polling, sleep],
        daemon=True
    )
    thread.start()
    if polling:
        return 'notify when the lesson can be reserved, please wait'
    else:
        return 'finding...'


def _background_find_lesson(
    user_id: str,
    studio: str,
    schedule: datetime,
    polling: bool = False,
    sleep: int = 30
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
    studio, schedule, polling, sleep = _parse_parameters(command.text.split())
    relocate = False
    thread = Thread(
        target=_background_reserve_lesson,
        args=[command.user_id, studio, schedule, relocate, polling, sleep],
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
    studio, schedule, polling, sleep = _parse_parameters(command.text.split())
    relocate = True
    thread = Thread(
        target=_background_reserve_lesson,
        args=[command.user_id, studio, schedule, relocate, polling, sleep],
        daemon=True
    )
    thread.start()
    if polling:
        return 'relocate the lesson when it becomes vacant, please wait'
    else:
        return 'relocating...'


def _background_reserve_lesson(
    user_id: str,
    studio: str,
    schedule: datetime,
    relocate: bool = False,
    polling: bool = False,
    sleep: int = 30
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
    polling = False
    sleep = 30
    if len(parameters) == 3:
        studio, date, start_time = parameters
    elif len(parameters) == 4:
        studio, date, start_time, polling = parameters
        polling = True if polling == 'auto' else False
    elif len(parameters) == 5:
        studio, date, start_time, polling, sleep = parameters
        polling = True if polling == 'auto' else False
        sleep = int(sleep)
    else:
        raise ValueError('invalid parameters')
    schedule = convert_datetime(date, start_time)
    return studio, schedule, polling, sleep


@app.post(
    '/scrape',
    response_model=str,
    dependencies=[Depends(verify_signature), Depends(verify_timestamp)]
)
async def scrape_lessons(request: Request):
    form = await request.form()
    command = SlackCommand(**form)
    if command.command != '/find':
        raise ValueError('endpoint does not match')
    start_date, lessons = command.text.split()
    start_date = convert_datetime(start_date)
    lessons = lessons.split(',')
    studio, schedule, polling, sleep = _parse_parameters(command.text.split())
    thread = Thread(
        target=_background_scrape_lessons,
        args=[command.user_id, studio, schedule, polling, sleep],
        daemon=True
    )
    thread.start()
    return 'scraping lessons, please wait'


def _background_scrape_lessons(
    user_id: str,
    start_date: datetime,
    lessons: List[str]
):
    with Client() as client:
        try:
            lessons = client.scrape_lessons(start_date, lessons)
            lessons = lessons2csv(lessons)
            file_upload(user_id, start_date, lessons)
        except Exception as e:
            logger.exception(f'{e}')
            logger.exception(user_id,
                             f'something wrong: {e.__class__.__name__}\n{e}')


def incoming_webhook(user_id, message):
    message = f'<@{user_id}> ' + message
    logger.info('webhook response\n' + message)
    requests.post(
        os.environ.get('FEELCYCLE_BOT_INCOMING_WEBHOOK'),
        data=json.dumps({'text': message}).encode('utf-8'))


def file_upload(user_id, start_date, content):
    url = "https://slack.com/api/file.upload"
    payload = {
        'token': os.environ.get('SLACK_OAUTH_ACCESS_TOKEN'),
        'channels': os.environ.get('SLACK_FEELBOT_CHANNEL_ID'),
        'title': f'{user_id}_lessons_from_{start_date}.csv',
        'content': content
    }
    requests.post(
        url,
        data=json.dumps(payload).encode('utf-8')
    )
