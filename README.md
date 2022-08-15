<!-- Generated with Nexin Django powered API template -->


# User Account Management System API

User Account Management System API


<!-- Default instructions -->

## GET STARTED

> If anything goes wrong, you can ask Victor N. for further assistance.

**Database**

This project is pre-configured with postgres. Follow this documentation on how to get started with postgres.

> [Install Postgres on Linux/Windows/Mac](http://postgresguide.com/setup/install.html)

After creating user(s) and database for this project, create a _**DATABASE URL**_, and add it to the **DATABASE_URL** in **env.sh** file.

The url must be formatted as this example bellow:
> postgres://user:password@host:port/db_name

_For localhost, host is **localhost**, and default port is **5432**_

**Create virtualenv**
```bash
virtualenv -p python3 venv
```

**Activate the virtualenv**
```bash
source venv/bin/activate
```

**Install requirements**
```bash
pip install -r requirements-vps.txt
```

**Generate [settings.ini](#) files** (For windows users, create the file manually):
```bash
cat settings.ini.example > settings.ini
```

*Open **[settings.ini](#)** files, and fill in all necessary **values.***

<br>

**Migrate**
```bash
python manage.py migrate
```

**Runserver**
```bash
python manage.py runserver
```

**Open project in browser**
```bash
http://localhost:8000/api-documentation
```

**Running tests**
```bash
python manage.py test
```
**Documentation**

By default, this project has a Swagger based documentation package called [drf-yasg](https://drf-yasg.readthedocs.io/en/stable/).

> For full documentation on configurations, please follow the [guide link.](https://drf-yasg.readthedocs.io/en/stable/)



**Working with Celery**

Celery is mainly used to perform background tasks which are usually not meant to be part of the request - response cycle.

> [Celery documentation](https://docs.celeryproject.org/en/latest/django/first-steps-with-django.html)



**Working with Celery Beat**

Celery beat is used to perform periodic tasks automatically.

> [Celery beat documentation](https://django-celery-beat.readthedocs.io/en/latest/)



**Deployment**

Django applications can be deployed in many ways, and on many different servers. Here are some useful documentations for some popular servers.

> [Ningx/gunicorn/postgresql on ubuntu server](https://rahmonov.me/posts/run-a-django-app-with-gunicorn-in-ubuntu-16-04/)

> [Heroku](https://devcenter.heroku.com/categories/working-with-django)

<!-- 
## CONFIGURE [PRE-COMMIT](https://pre-commit.com/)

**Install pre-commit requirements**
```bash
pre-commit install
```

**Run against all the files**
```bash
pre-commit run --all-files
``` -->


# Run with Docker

**Build project with docker compose**

```bash
docker-compose build
```
**Run project with docker compose**
```bash
docker-compose up
```

**Open project in browser**
```bash
http://0.0.0.0:8000/api-documentation
```