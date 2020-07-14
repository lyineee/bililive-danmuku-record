# -*- coding: utf-8 -*-
import asyncio
import json
import logging
import os
import sys
import threading
import time
import traceback

import requests as rq

import blivedm

# TODO maybe add bark notification when exception occor?
room_id_defalut = 92613

# log config
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%m/%d/%Y %H:%M:%S %p"
logging.basicConfig(
    filename="bili_danmaku.log",
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=DATE_FORMAT,
)
# output to stdout
log = logging.getLogger()
stdout_handler = logging.StreamHandler(sys.stdout)
log.addHandler(stdout_handler)


class MyBLiveClient(blivedm.BLiveClient):
    def __init__(self, room, live_start_time, **kw):
        super().__init__(room, ssl=True)
        self.d_file = open("./danmaku/{}.txt".format(live_start_time), "a")

        # write the info line (first line)
        live_info = {"live_start_time": live_start_time}
        self.d_file.writelines(json.dumps(live_info) + "\n")
        self.d_file.flush()

    _COMMAND_HANDLERS = blivedm.BLiveClient._COMMAND_HANDLERS.copy()

    async def _on_receive_danmaku(self, danmaku: blivedm.DanmakuMessage):
        logging.debug(f"{danmaku.uname}：{danmaku.msg} time:{danmaku.timestamp}")
        data = {
            "uid": danmaku.uid,
            "uname": danmaku.uname,
            "font_size": danmaku.font_size,
            "color": danmaku.color,
            "msg": danmaku.msg,
            "timestamp": danmaku.timestamp,
            "msg_type": danmaku.msg_type,
            "mode": danmaku.mode,
            "bubble": danmaku.bubble,
        }
        try:
            self.d_file.writelines(json.dumps(data) + "\n")
            self.d_file.flush()
            # uid 用户名 字体大小 颜色 内容 时间戳 是否为礼物（0:用户弹幕;1:礼物弹幕;2:主播礼物弹幕，抽奖）弹幕类型 超话？
        except:
            logging.error(traceback.format_exc())


def wait_live_end(client_future):
    while True:
        time_s = time.time()
        time.sleep(10)
        try:
            resp = rq.get(
                "https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByRoom?room_id={}".format(
                    room_id
                )
            )
            status = resp.json()["data"]["room_info"]["live_status"]
            logging.debug(
                "room status is:{} use time:{}".format(status, time.time() - time_s)
            )
            if status == 0:
                client_future.cancel()
        except:
            logging.error(traceback.format_exc())


async def main():
    # get live start time
    resp = rq.get(
        "https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByRoom?room_id={}".format(
            room_id
        )
    )
    live_start_time = resp.json()["data"]["room_info"]["live_start_time"]
    logging.info(
        "live start on {}".format(time.asctime(time.localtime(live_start_time)))
    )
    client = MyBLiveClient(room_id, ssl=True, live_start_time=live_start_time)
    # 如果SSL验证失败就把ssl设为False
    future = client.start()
    t1 = threading.Thread(target=wait_live_end, args=(future,))
    try:
        t1.start()
        await future
    finally:
        client.d_file.close()
        await client.close()
    logging.info("live end on {}".format(time.asctime()))


if __name__ == "__main__":
    env_val = os.getenv("ROOMID", "92613")
    try:
        room_id = int(env_val)
    except ValueError:
        log.fatal(
            "ROOMID error, please reset this envirment.get ROOMID: {}".format(env_val)
        )
    if room_id == room_id_defalut:
        log.warning("Your are using the default room id: {}".format(room_id_defalut))
    log.info("start record, record room id is {}".format(room_id))
    while True:
        time_s = time.time()
        time.sleep(5)
        try:
            resp = rq.get(
                "https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByRoom?room_id={}".format(
                    room_id
                )
            )
            status = resp.json()["data"]["room_info"]["live_status"]
            logging.debug(
                "room status is:{} use time:{}".format(status, time.time() - time_s)
            )
            if status == 1:
                asyncio.get_event_loop().run_until_complete(main())
        except:
            logging.error(traceback.format_exc())
