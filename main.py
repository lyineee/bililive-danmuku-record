# -*- coding: utf-8 -*-
import asyncio
import json
import logging
import os
import shutil
import sys

import time
import traceback
from logging.handlers import TimedRotatingFileHandler
from typing import Union

import requests as rq
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

import blivedm

room_id_defalut = 92613
log_level_default = logging.INFO
log_path_default = "./log"
tmp_dir = "./"
proxy_url = None

logger = logging.getLogger(__name__)
sentry_logger = logging.getLogger("sentry")


def strip_sensitive_data(event, hint):
    if event["logger"] == "sentry":
        return event


def log_config(log_level, log_path, dsn=None):
    try:  # Setting log level
        logger.setLevel(log_level)
    except ValueError or TypeError:
        logger.warning(
            "Wrong LOGLEVEL envirment, log level set to default: {}".format(
                log_level_default
            )
        )
        logger.setLevel(log_level_default)

    logger.info("Log level: {}".format(logging._levelToName[logger.level]))

    LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
    DATE_FORMAT = "%m/%d/%Y %H:%M:%S %p"
    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)

    if log_path == log_path_default:
        logger.warning("Using default log path {}".format(log_path_default))
    # create log directory if needed
    if not os.path.exists(log_path):
        logger.info("Log dir not found, creating one.")
        os.mkdir(log_path)

    # output to file
    fhlr = TimedRotatingFileHandler(
        filename=log_path + "/danmaku_record.log", when="W0", backupCount=4
    )
    fhlr.setFormatter(formatter)
    logger.addHandler(fhlr)
    blivedm.logger.addHandler(fhlr)

    # output to stdout
    chlr = logging.StreamHandler(sys.stdout)
    chlr.setFormatter(formatter)
    logger.addHandler(chlr)
    blivedm.logger.addHandler(chlr)

    # sentry event
    if dsn:
        sentry_logging_handler = LoggingIntegration(
            level=logging.INFO,  # Capture info and above as breadcrumbs
            event_level=logging.ERROR,  # Send errors as events
        )
        logger.info("Try to connect to dsn server: {}".format(dsn))
        sentry_sdk.init(
            dsn=dsn,
            integrations=[sentry_logging_handler],
            max_breadcrumbs=30,
            before_send=strip_sensitive_data,
        )
    else:
        logger.warning("Not provide dsn url, will not use it.")


class MyBLiveClient(blivedm.BLiveClient):
    def __init__(self, room, live_start_time, **kw):
        super().__init__(room, ssl=True)
        tmp_filename = "{}tmp-{}.txt".format(tmp_dir, live_start_time)
        self.d_file = open(tmp_filename, "a")

        # write the info line (first line), if file is blank
        if not self.d_file.tell():
            logger.info(
                "Danmaku file {} already exist, continue recording".format(tmp_filename)
            )
            live_info = {"live_start_time": live_start_time, "room_id": room_id}
            self.d_file.writelines(json.dumps(live_info) + "\n")
            self.d_file.flush()

    _COMMAND_HANDLERS = blivedm.BLiveClient._COMMAND_HANDLERS.copy()

    async def _on_receive_danmaku(self, danmaku: blivedm.DanmakuMessage):
        logger.debug(f"{danmaku.uname}：{danmaku.msg} time:{danmaku.timestamp}")
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
        except IOError as e:
            logger.error("{}, detail:\n{}".format(e, traceback.format_exc(limit=2)))
            sentry_logger.exception("Network error", extra=e)


async def wait_live_end():
    """
    @description: Wait until live end
    """

    while True:
        time_s = time.time()
        await asyncio.sleep(10)
        try:
            resp = rq.get(
                "https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByRoom?room_id={}".format(
                    room_id
                )
            )
            status = resp.json()["data"]["room_info"]["live_status"]
            logger.debug(
                "room status is:{}, interval:{}".format(status, time.time() - time_s)
            )
            if status == 0:
                transfer_tmp_file() # copy file there in case file overwrite
                break
        except TypeError as e:
            logger.debug(
                "Fail to get the room ({}) status in wait_live_end, will try soon, detail {}".format(
                    room_id, e
                ),
            )
            await asyncio.sleep(10)

        except Exception as e:
            logger.error(
                "Unknown error {} occur, detail: \n{}".format(
                    e, traceback.format_exc(limit=2)
                )
            )
            sentry_logger.exception("Error when getting room info", extra=e)
            await asyncio.sleep(10)


def transfer_tmp_file():
    for file_name in os.listdir(tmp_dir):
        if os.path.isfile(tmp_dir + file_name):
            prefix = os.path.splitext(file_name)[0].split("-")[0]
            if prefix == "tmp":
                name = os.path.splitext(file_name)[0].split("-")[-1]
                logger.info(
                    "Copying tmp file {} to row danmaku folder".format(file_name)
                )
                shutil.copy(tmp_dir + file_name, "./danmaku/" + name + ".json")
                os.remove(tmp_dir + file_name)


async def main_loop(live_start_time):
    logger.info(
        "live start on {}".format(time.asctime(time.localtime(live_start_time)))
    )
    client = MyBLiveClient(room_id, ssl=True, live_start_time=live_start_time)
    # 如果SSL验证失败就把ssl设为False
    client.start()
    try:
        await wait_live_end()
    finally:
        client.d_file.close()
        await client.close()
        # transfer_tmp_file()
    logger.info("live end on {}".format(time.asctime()))


def send_notif_bark(bark_token):
    if bark_token is not None:
        title = "ZBL"
        url = "https://live.bilibili.com/92613"
        try:
            logger.info("Sending notification to bark {}".format(bark_token))
            rq.get("https://api.day.app/{}/{}?url={}".format(bark_token, title, url))
        except Exception as e:
            logger.error(
                "Error when sending notificaiton to bark, detail: {}".format(e)
            )
            pass


def log_format(key: str, value: Union[str, int, float, None]):
    trim_value = str(value)[:25]
    return str(key).ljust(15, " ") + trim_value.rjust(25, " ")


if __name__ == "__main__":
    # log config
    env_log_path = os.getenv("LOG_PATH", log_path_default)
    env_log_level = os.getenv("LOG_LEVEL", log_level_default)
    env_dsn = os.getenv("DSN", None)
    env_roomid = os.getenv("ROOMID", room_id_defalut)
    env_bark_token = os.getenv("BARK_TOKEN")
    log_config(env_log_level, env_log_path, env_dsn)
    room_id = room_id_defalut

    logger.info("------------- Run argument -------------")
    logger.info(log_format("Room id:", room_id))
    logger.info(log_format("Log level:", env_log_level))
    logger.info(log_format("Log path:", env_log_path))
    logger.info(log_format("Bark token:", env_bark_token))
    logger.info(log_format("DSN:", env_dsn))
    logger.info("------------- End argument -------------")

    try:
        room_id = int(env_roomid)
    except ValueError:
        logger.error(
            "ROOMID error, please reset this envirment.get ROOMID: {}".format(
                env_roomid
            )
        )
    if room_id == room_id_defalut:
        logger.warning("Your are using the default room id: {}".format(room_id_defalut))
    logger.info("start record, record room id is {}".format(room_id))

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
            logger.debug(
                "room status resp is:{} use time:{}".format(
                    resp.json(), time.time() - time_s
                )
            )
            if status == 1:
                live_start_time = resp.json()["data"]["room_info"]["live_start_time"]
                send_notif_bark(env_bark_token)
                asyncio.get_event_loop().run_until_complete(main_loop(live_start_time))
                time.sleep(20)  # Maybe would not return None after live end
        except TypeError as e:
            logger.debug(
                "Fail to get the room ({}) status, will try soon, detail {}".format(
                    room_id, e
                ),
            )
            time.sleep(10)
        except json.decoder.JSONDecodeError as e:
            logger.debug(
                "Fail to get the room ({}) status, will try soon, detail {}".format(
                    room_id, e
                ),
            )
            logger.debug("Respond content is {}".format(resp.content))
        except Exception as e:
            logger.error(
                "Unknown error {} occur, detail: \n{}".format(
                    e, traceback.format_exc(limit=2)
                )
            )
            # sentry_logger.exception("Error when getting room info", extra=e)
            time.sleep(10)
