FROM python:3.9-slim

RUN mkdir -p /var/logs/app && touch /var/logs/app/app.log && chmod 666 /var/logs/app/app.log

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "app.py"]  