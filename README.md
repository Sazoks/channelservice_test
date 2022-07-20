# ChannelService
Сервис для мониторинга GoogleSheet-таблиц. Разрабатывался в качестве тестового задания.

## Содержание
1. О проекте
2. Установка
3. Как использовать
4. Будущее проекта
5. Мысли разработчика

## 1. О проекте
Проект представляет собой сервис для автоматического сбора данных о заказах из Google-таблицы и их синхронизации с БД.
Сервис предоставляет веб-интерфейс, где пользователь может видеть график данных, а также таблицу с новым столбцом - стоимостью заказа в рублях.

!!! ЗДЕСЬ КАРТИНКА ВЕБ-МОРДЫ !!!

Суть в том, что пользователь может не отвлекаясь редактировать Google-таблицу, вносить, править, удалять данные, а сервис сам периодически синхронизирует данные. Также сервис умеет контролировать сроки поставок новых заказов и высылать отчёт о просроченных заказах в Telegram.

## 2. Установка
Для установки и запуска сервиса понадобятся следующие компоненты:
- Django на backend'e.
- React на frontend'e.
- Web-сервер Nginx.
- Асинхронная очередь сообщений Celery.
- Брокер сообщений Redis/RabbitMQ (на выбор).

Поэтому, вы можете либо установить все компоненты вручную, либо воспользоваться Docker Compose и поднять всю эту вереницу технологий одной кнопкой. Для этого сделайте следующие действия:
1. Склонируйте этот репозиторий.
2. Задайте все необходимые переменные окружения в файле ```/django/.env```.
3. Откройте консоль в папке проекте (в папке, где лежит ```docker-compose.yml```).
4. Введите команды: 
```bash
docker-compose build
docker-compose up
```
5. После запуска всех контейнеров откройте в отдельном окне консоль и сделайте миграции: 
```bash 
docker-compose exec django python manage.py migrate --noinput
```
6. Проект работает!

## 3. Как использовать
На данный момент сервис может работать только с одной подключенной Google-таблицей.
Чтобы сервис мог пользовать Google Sheet API, необходимо выполнить следующие действия:
1. Подключить Google Sheet API в своем Google Cloud.
2. Создать сервисный аккаунт, сгенерировать для него учетные данные в формате json и положить их в папку creds в проекте. Также нужно не забыть указать название файлов с учетными данными в файле .env.
3. В закрытой Google-таблице дать доступ на email сервисного аккаунта.
4. Прописать в файл переменных окружения требуемые права для сервиса (readonly), указать id таблицы и диапазон ячеек для чтения.
5. Указать другие настройки в файле переменных окружения, которые требуются в settings.py.
6. Для подключения уведомлений в Telegram необходимо создать бота, прописать его токен в переменных окружения, а также задать список id пользователей, которые могут получать уведомления.

## 4. Будущее проекта
На данный момент проект находится в сыром виде. В ближайшем будущем разработчик добавит:
- Личные кабинеты пользователей.
- Опциональность возможности уведомлений в Telegram.
- Подключение нескольких таблиц для каждого пользователя.
- Трекер времени работы воркеров на каждой таблице. Пользователь не сможет бесконечно использовать воркеров для обработки своих таблиц, поэтому в теории можно добавить монетизацию. Время - деньги.
- Доработать документацию по настройке и запуску проекта.
- Возможность кастомизировать свои таблицы. Сейчас сервис умеет работать только с таблицей заказов.

## 5. Мысли разработчика
Проект мне очень понравился. На первый взгляд показался довольно простым, однако впоследствии появлялись весьма интересные ситуации, заставляющие крепко подумать. Например, аутентификация в Google Cloud из вьюшки работает хорошо, а из воркера Celery - нет. Или задачка на синхронизацию данные из таблицы и из БД. Также появилась неплохая возможность попробовать React, т.к. до этого с ним никогда не работал. Довольно неплохо, в сравнении с HTML/CSS/jQuery кажется чем-то ультра-современным.
