from datetime import datetime

from fastapi import FastAPI

from .client import Client
from .models import Lesson
from loguru import logger


app = FastAPI()


@app.get('/find', response_model=Lesson)
async def find_lesson(
    studio: str,
    schedule: datetime,
    polling: bool = False,
    sleep: int = 30
):
    with Client() as client:
        lesson = client.find_lesson(studio, schedule, polling=polling, sleep=int(sleep))
    pref='lesson information\n'
    incoming_webhook(lesson.text(prefix=pref))
    return lesson


@app.post('/reserve', response_model=Lesson)
async def reserve_lesson(
    studio: str,
    schedule: datetime,
    polling: bool = False,
    sleep: int = 30
):
    with Client() as client:
        success, lesson = client.reserve_lesson(
            studio, schedule, relocate=False, polling=polling, sleep=int(sleep))

    pref = 'reservation success!\n' if success else 'reservation failed\n'
    incoming_webhook(lesson.text(prefix=pref))
    return lesson


@app.post('/relocate', response_model=Lesson)
async def reserve_lesson(
    studio: str,
    schedule: datetime,
    polling: bool = False,
    sleep: int = 30
):
    with Client() as client:
        success, lesson = client.reserve_lesson(
            studio, schedule, relocate=True, polling=polling, sleep=int(sleep))

    pref = 'reservation success!\n' if success else 'reservation failed\n'
    incoming_webhook(lesson.text(prefix=pref))
    return lesson


def incoming_webhook(message):
    logger.info('webhook response\n' + message)
    requests.post(
        os.environ.get('FEELCYCLE_BOT_INCOMING_WEBHOOK'),
        data=json.dumps({'text': message}).encode('utf-8'))
