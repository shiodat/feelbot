import os
import random
import time

from datetime import datetime
from datetime import timedelta
from typing import Optional, Union, Tuple, List

from dotenv import load_dotenv
from loguru import logger
from pydantic import SecretStr
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.select import Select

from .models import Lesson, Reservation
from .utils import convert_datetime


MYPAGE_URL = 'https://www.feelcycle.com/feelcycle_reserve/mypage.php'
RESERVE_URL = 'https://www.feelcycle.com/feelcycle_reserve/reserve.php'


class NotLoginError(Exception):
    pass


class LoginError(Exception):
    pass


class StudioSelectionError(Exception):
    pass


class LessonNotFoundError(Exception):
    pass


def is_login(driver: WebDriver) -> bool:
    driver.get(MYPAGE_URL)
    try:
        driver.find_element_by_class_name('log_in_id')
        return True
    except NoSuchElementException:
        return False


def login(
    driver: WebDriver,
    username: str,
    password: SecretStr,
    timeout: int = 5
) -> bool:
    if is_login(driver):
        return True
    else:
        WebDriverWait(driver, timeout)
        driver.find_element_by_name('login_id').send_keys(username)
        driver.find_element_by_name('login_pass').send_keys(password)
        driver.find_element_by_class_name('submit_b') \
              .find_element_by_tag_name('input').click()
        return is_login(driver)


def select_studio(
    driver: WebDriver,
    studio: str
) -> None:
    if not is_login(driver):
        raise NotLoginError()

    driver.get(RESERVE_URL)
    selector = Select(driver.find_element_by_name('tenpo'))
    for option in selector.options:
        name = option.text
        if '（' not in name or '）' not in name:
            continue
        name = name.replace('）', '').split('（')[1]
        name = name.replace(' ', '').replace('　', '')
        if name == studio:
            selector.select_by_value(option.get_attribute('value'))
            return
    raise StudioSelectionError()


def find_lesson(
    driver: WebDriver,
    studio: str,
    schedule: datetime,
    return_element: bool = False
) -> Union[Optional[Lesson], Tuple[Optional[Lesson], Optional[WebElement]]]:
    if not is_login(driver):
        raise NotLoginError()

    driver.get(RESERVE_URL)
    select_studio(driver, studio)
    for _ in range(3):
        for div in driver.find_elements_by_tag_name('div'):
            if div.get_attribute('id') not in ('day_', 'day__b'):
                continue
            lesson_date =\
                div.find_element_by_tag_name('div').text.split('(')[0]
            dt = convert_datetime(lesson_date, clock=None)
            if schedule.date() != dt.date():
                continue
            valid_units = ['unit', 'unit_past', 'unit_reserved']
            lesson_elements = sum([div.find_elements_by_class_name(unit)
                                  for unit in valid_units], [])
            for lesson_element in lesson_elements:
                contents = lesson_element.find_elements_by_tag_name('p')
                start_time = contents[0].text.split('～')[0]
                dt = convert_datetime(lesson_date, clock=start_time)
                if abs(schedule - dt) > timedelta(minutes=1):
                    continue
                program = contents[1].text
                instructor = contents[2].text
                unit = lesson_element.get_attribute('class')
                current_time = datetime.now()
                if current_time < schedule and unit == 'unit_past':
                    unit = 'unit_full'
                status = {
                    'unit': Reservation.VACANT,
                    'unit_full': Reservation.FULL,
                    'unit_past': Reservation.PAST,
                    'unit_reserved': Reservation.RESERVED,
                }[unit]
                lesson = Lesson(schedule=schedule,
                                studio=studio,
                                program=program,
                                instructor=instructor,
                                status=status)
                logger.info(lesson.json())
                return (lesson, lesson_element) if return_element else lesson
        driver.find_element_by_id('week') \
              .find_elements_by_tag_name('a')[1].click()

    return_values = (None, None) if return_element else None
    return return_values


def reserve_lesson(
    driver: WebDriver,
    studio: str,
    schedule: datetime,
    relocate: bool = False
) -> Tuple[bool, Optional[Lesson]]:
    lesson, lesson_element =\
        find_lesson(driver, studio, schedule, return_element=True)
    if lesson is None:
        return False, None
    if relocate:
        if lesson.status != Reservation.RESERVED:
            return False, lesson
    else:
        if lesson.status in (Reservation.FULL, Reservation.PAST):
            return False, lesson
        if lesson.status == Reservation.RESERVED:
            return True, lesson

    lesson_element.click()
    success = False
    for seat_element in driver.find_elements_by_class_name('number')[::-1]:
        seat_link = seat_element.find_element_by_tag_name('a')
        if seat_link.get_attribute('class') not in ('thickbox', ''):
            continue
        seat_link.click()
        if relocate:
            time.sleep(1)
            Alert(driver).accept()
        driver.find_elements_by_class_name('coment')[1] \
              .find_elements_by_tag_name('a')[1] \
              .click()
        success = True
        break
    return success, lesson


def scrape_studio_lessons(
    driver: WebDriver,
    studio: str,
    start_date: datetime
) -> List[Lesson]:
    if not is_login(driver):
        raise NotLoginError()

    driver.get(RESERVE_URL)
    select_studio(driver, studio)

    lessons = []
    while True:
        week_date = driver.find_element_by_id('week') \
                          .find_element_by_name('setdate') \
                          .get_attribute('value')
        week_date = datetime.strptime(week_date, '%Y/%m/%d')
        if week_date < start_date:
            break

        for div in driver.find_elements_by_tag_name('div'):
            if div.get_attribute('id') not in ('day_', 'day__b'):
                continue
            lesson_date =\
                div.find_element_by_tag_name('div').text.split('(')[0]
            lesson_datetime = convert_datetime(lesson_date, clock=None)

            lesson_elements = div.find_elements_by_class_name('unit_reserved')

            for lesson_element in lesson_elements:
                contents = lesson_element.find_elements_by_tag_name('p')
                start_time = contents[0].text.split('～')[0]
                lesson_datetime =\
                    convert_datetime(lesson_date, clock=start_time)
                program = contents[1].text
                instructor = contents[2].text
                lesson = Lesson(schedule=lesson_datetime,
                                studio=studio,
                                program=program,
                                instructor=instructor,
                                status=Reservation.RESERVED)
                lessons.append(lesson)
                logger.info(lesson.json())
        driver.find_element_by_id('week') \
              .find_elements_by_tag_name('a')[0].click()
    lessons = sorted(lessons, key=lambda lesson: lesson.schedule)
    return lessons


def scrape_lessons(
    driver: WebDriver,
    studios: List[str],
    start_date: datetime
) -> List[Lesson]:
    lessons = sum([scrape_studio_lessons(driver, studio, start_date)
                  for studio in studios], [])
    lessons = sorted(lessons, key=lambda lesson: lesson.schedule)
    return lessons


def get_driver() -> WebDriver:
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)
    return driver


class Client(object):

    MAX_RETRY = 10

    def __init__(self):
        self.driver = get_driver()
        self.count = 0
        load_dotenv(verbose=True)

    def __enter__(self):
        return self

    def __exit__(self, ex_type, ex_value, trace):
        self.driver.quit()

    def _refresh_driver(self):
        if self.count > self.MAX_RETRY:
            self.count = 0
            self.driver.quit()
            time.sleep(5)
            self.driver = get_driver()
        else:
            self.count += 1

    def is_login(self) -> bool:
        return is_login(self.driver)

    def login(self) -> None:
        if self.is_login():
            return
        username = os.environ.get('FEELCYCLE_USERNAME')
        password = os.environ.get('FEELCYCLE_PASSWORD')
        success = login(self.driver, username, password)
        if not success:
            LoginError()

    def select_studio(self, studio: str) -> None:
        self.login()
        select_studio(self.driver, studio)

    def find_lesson(
        self,
        studio: str,
        schedule: datetime,
        polling: bool = False,
        sleep: int = 30,
    ) -> Lesson:
        def _find():
            self.login()
            lesson = find_lesson(self.driver, studio, schedule, False)
            if lesson is None:
                raise LessonNotFoundError()
            return lesson

        if polling:
            while True:
                self._refresh_driver()
                try:
                    lesson = _find()
                except TimeoutException:
                    logger.info('timeout error, retry')
                    continue
                if lesson.status == Reservation.FULL:
                    time.sleep(random.randint(int(sleep*0.5), int(sleep*1.5)))
                else:
                    return lesson
        else:
            return _find()

    def reserve_lesson(
        self,
        studio: str,
        schedule: datetime,
        relocate: bool = False,
        polling: bool = False,
        sleep: int = 30,
    ) -> Tuple[bool, Optional[Lesson]]:
        def _reserve():
            self.login()
            success, lesson = reserve_lesson(
                self.driver, studio, schedule, relocate=relocate)
            if lesson is None:
                raise LessonNotFoundError()
            if success:
                lesson = find_lesson(self.driver, studio, schedule, False)
                if lesson is None:
                    raise LessonNotFoundError()
            return success, lesson

        if polling:
            while True:
                self._refresh_driver()
                try:
                    success, lesson = _reserve()
                except TimeoutException:
                    logger.info('timeout error, retry')
                    continue
                if lesson is None:
                    return False, None
                elif (relocate is False and lesson.status == Reservation.FULL) or \
                     (relocate is True and success is False):
                    time.sleep(random.randint(int(sleep*0.5), int(sleep*1.5)))
                else:
                    return success, lesson
        else:
            return _reserve()

    def scrape_lessons(
        self,
        studios: List[str],
        start_date: datetime,
    ) -> List[Lesson]:
        self.login()
        lessons = scrape_lessons(self.driver, studios, start_date)
        return lessons
