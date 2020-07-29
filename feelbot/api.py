from datetime import datetime

from fastapi import FastAPI

from .client import Client
from .models import Lesson


app = FastAPI()
client = Client()


@app.get('/find', response_model=Lesson)
async def find_lesson(
    studio: str,
    schedule: datetime,
    polling: bool = False
):
    lesson = client.find_lesson(studio, schedule, polling=polling)
    return lesson


@app.post('/reserve', response_model=Lesson)
async def reserve_lesson(
    studio: str,
    schedule: datetime,
    polling: bool = False
):
    success, lesson = client.reserve_lesson(
        studio, schedule, polling=polling, refresh=True)
    return lesson
