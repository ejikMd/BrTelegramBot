FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8000
ENV TELEGRAM_BOT_TOKEN=your_bot_token_here

CMD ["python", "main.py"]
