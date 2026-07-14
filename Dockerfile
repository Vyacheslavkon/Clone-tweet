FROM python:3.12-slim

ARG USER_ID=1000
ARG GROUP_ID=1000

RUN groupadd -g $GROUP_ID appuser && \
    useradd -u $USER_ID -g appuser -m -s /bin/bash appuser

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /application

RUN  pip install --upgrade pip
COPY requirement.txt .
RUN pip install --no-cache-dir -r requirement.txt

COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8000

CMD ["python", "main.py"]