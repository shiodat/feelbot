from enum import Enum
from datetime import datetime
from typing import List

from pydantic import BaseModel


class Reservation(Enum):
    RESERVED = 'RESERVED'
    VACANT = 'VACANT'
    FULL = 'FULL'
    PAST = 'PAST'


class Lesson(BaseModel):
    schedule: datetime
    studio: str
    program: str
    instructor: str
    status: Reservation

    def text(self, prefix='', suffix=''):
        msg = ''
        msg += prefix
        msg += f'lesson: {self.schedule.strftime("%m/%d %H:%M")} ' \
               f'{self.program} ({self.instructor}) @{self.studio}\n' \
               f'status: {self.status.value}'
        msg += suffix
        return msg

    @staticmethod
    def csv_header():
        return 'datetime,studio,program,instructor'

    def csv_row(self):
        msg = f'{self.schedule.strftime("%m/%d %H:%M")},' \
              f'{self.studio},{self.program},{self.instructor}'
        return msg


def lessons2csv(lessons: List[Lesson]):
    csv_data = Lesson.csv_header() + '\n'
    for lesson in lessons:
        csv_data += lesson.csv_row() + '\n'
    return csv_data
