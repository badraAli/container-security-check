FROM python:3.9-slim

RUN mkdir -p /var/log/app 
RUN touch /var/log/app/app.log 
RUN chmod 666 /var/log/app/app.log

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "app.py"]  