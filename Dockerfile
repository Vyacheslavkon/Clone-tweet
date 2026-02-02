FROM python:3.12

WORKDIR /application

RUN  pip install --upgrade pip
COPY requirement.txt .
RUN pip install --no-cache-dir -r requirement.txt

COPY . .

EXPOSE 8000

CMD ["python", "main.py", "--reload", "--log-level", "debug"]