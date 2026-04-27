#!/bin/sh
# Компилируем переводы
pybabel compile -d financial_bot/locales
# Запускаем то, что передано в Dockerfile (или compose)
exec "$@"
