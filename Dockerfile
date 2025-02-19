FROM python:3.13-alpine

WORKDIR /app
ADD requirements.txt state2slack.py .
RUN pip install --no-cache-dir -r requirements.txt

CMD [ "python3", "state2slack.py" ]