# YandexBackendSchool2
# Вторая попытка пройти в ШБР
Yet Another Numerical Distinct XXX
> Никогда не сдавайтесь — никогда, никогда, никогда, никогда, ни в большом, ни в малом, ни в крупном, ни в мелком, никогда не сдавайтесь, если это не противоречит чести и здравому смыслу. Никогда не поддавайтесь силе, никогда не поддавайтесь очевидно превосходящей мощи вашего противника.
>> Уинстон Черчилль

Бэкенд сервис на Python: Flask + Flask Blueprints + SqlAlchemy + Nginx + gunicorn + Docker


### API specification

Реализованы следующие сервисы API

| /imports | /delete/{id} | /updates | /node/{id}/history |
| ------ | ----------- | ------- | ------------ |

Их спецификация подробно описана в в /enrollment/openapi.yaml

### Deployment

## Docker way
Для запуска проекта через докер необходимо создать персистентную область контейнера. Файл базы данных находится по адресу /YandexBackendSchool2/db/. Пример создания  и использования value для Docker контейнера:
```console
sudo docker volume create --name data
sudo docker build -t yandexbackend:v0.1 YandexBackendSchool2/
sudo docker run -d -v data:/YandexBackendSchool2/db/ --publish 80:80 --restart=always yandexbackend:v0.1
```
В Dockerfile описан метод запуска приложения средством сборки. В данной реализации используется gunicorn с параметрами "-w","12", "--threads", "4", "--bind", "0.0.0.0:80"

Полная инструкция по запуску на удаленном сервере:
```console
git clone https://github.com/mariklolik/YandexBackendSchool2.git
sudo docker volume create --name data
sudo docker build -t yandexbackend:v0.2 YandexBackendSchool2/
sudo docker run -d -v data:/YandexBackendSchool2/db/ --publish 80:80 --restart=always yandexbackend:v0.2
```
