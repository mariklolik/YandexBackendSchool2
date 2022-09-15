# syntax=docker/dockerfile:1

FROM python:3.8-slim-buster

WORKDIR /YandexBackend22

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN pip install --upgrade pip
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .


EXPOSE 80
CMD ["gunicorn"  ,"-w","30", "--threads", "4", "--bind", "0.0.0.0:80", "app:app"]
#CMD ["python3","wsgi.py", "-m" , "flask", "run","--host=0.0.0.0"]
