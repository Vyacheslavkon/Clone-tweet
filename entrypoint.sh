#!/bin/sh
# Компилируем переводы
pybabel compile -d financial_bot/locales
# Запускаем то, что передано в Dockerfile (или compose)
python -c "from rapidocr_onnxruntime import RapidOCR; RapidOCR()"

exec "$@"
