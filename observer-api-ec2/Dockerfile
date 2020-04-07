FROM tiangolo/meinheld-gunicorn:python3.7

RUN pip install --upgrade pip && \
    pip install --no-cache-dir aiohttp boto3

COPY ./ /app

CMD [ "gunicorn", "-w", "1", "main:app", "--chdir /app", "-b 0.0.0.0:80", "-k aiohttp.worker.GunicornWebWorker", "--reload" ]