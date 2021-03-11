import logging
import os
from typing import Collection

import pymongo
from pymongo.database import Database
from pymongo.errors import ConnectionFailure
from pymongo.mongo_client import MongoClient


class MongoDB(object):
    mongo_client = None

    def __init__(self):
        self.env_dburl = os.getenv("MONGODB", "mongodb://localhost:27017/")

    def connect(self):
        # connect to db
        dburl = self.env_dburl
        try:
            logging.info("Connecting to the mongodb {}".format(dburl))
            self.mongo_client = pymongo.MongoClient(dburl)
            self.mongo_client.server_info()
        except ConnectionFailure as e:
            logging.fatal(
                "Can not connect to MongoDB, please check the connection or the envirment. Input MONGODB is {}, msg: {}".format(
                    dburl, e.args
                )
            )
            exit(1)
        else:
            logging.info("Connect success")


db = MongoDB()

def db_connect():
    db.connect()


def get_database():
    return db.mongo_client


def get_info_col(client: MongoClient):
    db: Database = client["bili_danmaku"]
    info_col: Collection = db["info"]
    return info_col


def get_data_col(client: MongoClient):
    db: Database = client["bili_danmaku"]
    data_col: Collection = db["data"]
    return data_col
