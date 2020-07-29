from enum import Enum
from datetime import datetime

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
