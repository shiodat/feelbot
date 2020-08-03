FROM tiangolo/uvicorn-gunicorn-fastapi:latest

RUN apt-get update \
    && apt-get install -y wget \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update -qq \
    && apt-get install -y google-chrome-stable python3-selenium

WORKDIR /app
COPY ./requirements.txt /app/requirements.txt
COPY ./feelbot /app/feelbot

RUN pip install -U setuptools pip \
    && pip install -r /app/requirements.txt

EXPOSE 80
CMD ["uvicorn", "feelbot.slack.api:app", "--host", "0.0.0.0", "--port", "80"]

