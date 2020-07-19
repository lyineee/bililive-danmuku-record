FROM python:3

WORKDIR /usr/src/app

ENV TIME_ZONE=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TIME_ZONE /etc/localtime && echo $TIME_ZONE > /etc/timezone

COPY ["main.py", "blivedm.py", "requirements.txt", "./"]

RUN pip install --no-cache-dir -r requirements.txt

CMD [ "python", "./main.py" ]
