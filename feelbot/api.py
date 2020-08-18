from datetime import datetime
from typing import List

from fastapi import FastAPI

from .client import Client
from .models import Lesson


app = FastAPI()


@app.get('/find', response_model=Lesson)
async def find_lesson(
    studio: str,
    schedule: datetime,
    polling: bool = False,
    sleep: int = 30
):
    with Client() as client:
        lesson = client.find_lesson(
            studio, schedule, polling=polling, sleep=int(sleep))
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

    return lesson


@app.post('/relocate', response_model=Lesson)
async def relocate_lesson(
    studio: str,
    schedule: datetime,
    polling: bool = False,
    sleep: int = 30
):
    with Client() as client:
        success, lesson = client.reserve_lesson(
            studio, schedule, relocate=True, polling=polling, sleep=int(sleep))
    return lesson


@app.post('/scrape', response_model=List[Lesson])
async def scrape_lessons(
    studios: List[str],
    start_date: datetime,
):
    with Client() as client:
        lessons = client.scrape_lessons(studios, start_date)
    return lessons
