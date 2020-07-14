# bililive-danmaku-record
create a docker container to record bilibili live danmaku

# Uasage
docker run -e ROOMID=92613 --name bili -v /path/to/your/danmaku/folder/:/usr/src/app/danmaku lyine/bililive-danmuku-record

You can change the envirment ROOMID in main.py to record other room 
