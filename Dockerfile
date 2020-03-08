FROM python:3.7-alpine
RUN mkdir /app
WORKDIR /app
ADD requirements.txt /app
RUN pip install -r requirements.txt
ADD tools.py /app
RUN ln -s /app/tools.py /usr/local/bin/redis-tools

ENTRYPOINT ["python", "tools.py"]