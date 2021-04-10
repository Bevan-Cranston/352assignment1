FROM python:3.8.9-buster

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY /app .

CMD ["python", "assignment1.py"]