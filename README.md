# Diabeat

## Requirements
- [Python 3](https://www.python.org/)
- [Node.js](https://nodejs.org/)
- Git clone this project

## Installation

```sh
# Project root directory

cd ./glucose-BE/glucoseBE
# It is recommend to use venv instead of global environment
# Activate venv here if you have one
pip install -r requirements.txt

cd ../glucose-FE
npm -g pnpm
pnpm install
```

## Run server

```sh
# Project root directory

cd ./glucose-BE/glucoseBE
# Activate venv here if you have one
python manage.py migrate
python manage.py runserver 0.0.0.0:8000 --noreload
```

## Run web demo

```sh
# Project root directory

cd ./glucose-FE
pnpm dev --open
```
