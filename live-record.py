from logging import info
import time
from typing import Union
from pymongo.collection import Collection
from requests.models import get_cookie_header
from mongo import MongoDB, get_data_col, get_info_col, db_connect, db
from bili_api import (
    Danmaku,
    LiveRecordInfo,
    get_live_info,
    get_danmaku,
    get_live_record_list,
)
from bson.objectid import ObjectId


class MongoDanmaku(Danmaku):
    def __init__(self, id, **kwargs) -> None:
        # print(kwargs.text)
        super().__init__(**kwargs)
        if not isinstance(id, ObjectId):
            id = ObjectId(id)
        self.creator = id


def main_loop():
    db_connect()
    record_list = get_live_record_list(92613)
    info_col = get_info_col(db.mongo_client)
    print("Record list count: {}".format(len(record_list)))
    for record in record_list:
        if not info_col.count_documents({"rid": record.rid}):
            print("Start to crawling record {}".format(record.rid))
            try:
                save_record(record.rid)
            except Exception as e:
                print("Fail in crawling record, rid is {}".format(record.rid))


def save_record(rid):
    info: LiveRecordInfo = get_live_info(rid)
    info_col: Collection = get_info_col(db.mongo_client)
    result = info_col.insert_one(dict(info.live_info))
    for dm_info in info.dm_info.index_info:
        dm_list = get_danmaku(rid, dm_info.index)
        insert_list = []
        for item in dm_list:
            insert_data = MongoDanmaku(result.inserted_id, **dict(item))
            insert_list.append(dict(insert_data))
        data_col: Collection = get_data_col(db.mongo_client)
        data_col.insert_many(insert_list)


if __name__ == "__main__":
    main_loop()

