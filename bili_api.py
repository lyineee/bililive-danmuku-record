from typing import List
import requests as rq
import json
import logging
from dataclasses import dataclass

logger = logging.getLogger(__file__)


class MappingType:
    def __iter__(self):
        for k, v in self.__dict__.items():
            if isinstance(v, MappingType):
                yield k, dict(v)
            elif isinstance(v, list):
                yield k, [dict(d) for d in v]
            else:
                yield k, v


@dataclass
class LiveInfo(MappingType):
    danmu_num: int
    rid: str
    online: int
    room_id: int
    start_timestamp: int  # 时间戳 秒
    end_timestamp: int
    title: str
    uid: int


@dataclass
class Dms(MappingType):
    index: int
    md5: str
    total_num: int  # dm_info + interactive_info


@dataclass
class DmInfo(MappingType):
    index_info: List[Dms]
    num: int  # 弹幕 index 数
    total_num: int  # 弹幕与互动总数


@dataclass
class LiveRecordInfo(MappingType):
    dm_info: DmInfo
    live_info: LiveInfo


@dataclass
class Danmaku(MappingType):
    text: str
    nickname: str
    msg_type: int
    mobile_verify: bool
    is_admin: bool
    dm_type: int
    dm_mode: int  # 弹幕类型
    dm_fontsize: int
    dm_color: int
    ts: int  # 出现时间 单位：毫秒
    uid: int


@dataclass
class RecordListItem:
    start_timestamp: int
    rid: str


def bilibili_headers(referer=None, cookie=None):
    # a reasonable UA
    ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36"
    headers = {
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.5",
        "User-Agent": ua,
    }
    if referer is not None:
        headers.update({"Referer": referer})
    if cookie is not None:
        headers.update({"Cookie": cookie})
    return headers


def get_live_info(rid) -> LiveRecordInfo:
    url = "https://api.live.bilibili.com/xlive/web-room/v1/record/getInfoByLiveRecord?rid={}".format(
        rid
    )
    resp = rq.get(url, headers=bilibili_headers())
    try:
        resp_data = resp.json()
        if resp_data["code"] == 0:
            info_row = resp_data["data"]["live_record_info"]
            live_info = LiveInfo(
                danmu_num=info_row["danmu_num"],
                rid=info_row["rid"],
                online=info_row["online"],
                room_id=info_row["room_id"],
                start_timestamp=info_row["start_timestamp"],
                end_timestamp=info_row["end_timestamp"],
                title=info_row["title"],
                uid=info_row["uid"],
            )
            dms: List[Dms] = []
            for item in resp_data["data"]["dm_info"]["index_info"]:
                dm = Dms(
                    index=item["index"], md5=item["md5"], total_num=item["total_num"]
                )
                dms.append(dm)
            dm_info = DmInfo(
                index_info=dms,
                num=resp_data["data"]["dm_info"]["num"],
                total_num=resp_data["data"]["dm_info"]["total_num"],
            )
            logger.debug(dm_info)
            info = LiveRecordInfo(dm_info=dm_info, live_info=live_info)
            return info
    except json.decoder.JSONDecodeError as e:
        logger.error("Error when get live info, msg: {}".format(e.args))


def get_danmaku(
    rid: str = "R1Vx411w79V", index: int = 0, md5: str = None
) -> List[Danmaku]:
    url = "https://api.live.bilibili.com/xlive/web-room/v1/dM/getDMMsgByPlayBackID?rid={}&index={}".format(
        rid, index
    )
    resp = rq.get(url, headers=bilibili_headers())
    try:
        resp_data = resp.json()
        if resp_data["code"] == 0:
            if md5 and resp_data["data"]["md5"] != md5:
                raise Exception("Not passing md5 check")
            dm_list = []
            for dm in resp_data["data"]["dm"]["dm_info"]:
                d = Danmaku(
                    text=dm["text"],
                    nickname=dm["nickname"],
                    msg_type=dm["msg_type"],
                    mobile_verify=dm["mobile_verify"],
                    is_admin=dm["is_admin"],
                    dm_type=dm["dm_type"],
                    dm_mode=dm["dm_mode"],
                    dm_fontsize=dm["dm_fontsize"],
                    dm_color=dm["dm_color"],
                    ts=dm["ts"],
                    uid=dm["uid"],
                )
                dm_list.append(d)
            return dm_list
    except json.decoder.JSONDecodeError as e:
        logger.error("Error when get live info, msg: {}".format(e.args))
        raise
    except TypeError as e:
        logger.warning(
            "NoneType warning when fetching rid: {}, index: {}, may just be a blank chunk.".format(
                rid, index
            )
        )


def get_live_record_list(
    room_id: int, page: int = 1, page_size: int = 65
) -> List[RecordListItem]:
    """
    max record count: 64, so dont set page_size bigger than 65.
    """
    url = "https://api.live.bilibili.com/xlive/web-room/v1/record/getList?room_id={}&page={}&page_size={}".format(
        room_id, page, page_size
    )
    resp = rq.get(url, headers=bilibili_headers())
    try:
        resp_data = resp.json()
        if resp_data["code"] != 0:
            raise Exception("Return code not 0")
        record_list: List[RecordListItem] = []
        for item in resp_data["data"]["list"]:
            record_list.append(
                RecordListItem(
                    start_timestamp=item["start_timestamp"], rid=item["rid"],
                )
            )
        return record_list
    except json.decoder.JSONDecodeError as e:
        logger.error("Error when get live info, msg: {}".format(e.args))
        raise


if __name__ == "__main__":
    logger.debug("Debug Start")
    # print(get_danmaku()[0]["text"])
    # print(get_live_info("R15x411w7uA"))
    print(get_live_record_list(92613))
