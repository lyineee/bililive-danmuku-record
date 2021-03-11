from xml.dom import minidom as md
import json
import os
import cv2
import sys
import requests as rq
from zipfile import ZipFile
import uuid

class DanmakuGene(object):
    danmaku_data_raw = None
    live_start_time = None
    danmaku_data_sorted = None
    result_list = None
    video_info_url = "https://api.bilibili.com/x/player/pagelist?bvid={}"

    def __init__(self, danmaku_path):
        self.danmaku_path = danmaku_path
        self.video_time_pointer = 0
        self.read_danmaku(self.danmaku_path)

    def read_danmaku(self, path):
        file_name = os.path.splitext(os.path.split(path)[-1])[0]
        self.danmaku_data_raw = []
        with open(path, "r") as f:
            try:  # for compatibility to older danmaku file
                self.live_start_time = int(file_name.split(".")[0] + "000")
                f.readline()  # skip first line
            except ValueError:
                info = json.loads(f.readline())
                self.live_start_time = info["live_start_time"] * 1000
            for i in f:
                self.danmaku_data_raw.append(json.loads(i))

    def get_video_info(self, path="./video", bias=0) -> list:
        l = os.listdir(path)
        l.remove(".gitignore")
        l.sort(key=lambda x: int(os.path.splitext(x)[0]))
        time_list = [(0, bias)]
        for i in l:
            cap = cv2.VideoCapture(path + "/" + i)
            duration = int((cap.get(7) / cap.get(5)) * 1000)
            time_list.append((time_list[-1][1], time_list[-1][1] + duration))
        del time_list[0]
        return time_list

    def get_video_info_from_web(self, bvid) -> list:
        """
        in list item:
        duration: video last time, unit: second
        part: episode name
        page: episode index
        """
        data_url = self.video_info_url.format(bvid)
        try:
            data_resp = rq.get(data_url)
            data = data_resp.json()
        except:
            raise
        dict_slice_data = ["duration", "part", "page"]
        data_list = [
            {key: val for key, val in list_item.items() if key in dict_slice_data}
            for list_item in data["data"]
        ]
        return data_list

    def get_danmaku_by_time(self, start_time, end_time) -> list:
        """
        start_time and end_time unit is millisecond
        """
        # sort row data
        self.danmaku_data_sorted = sorted(
            self.danmaku_data_raw, key=lambda x: x["timestamp"]
        )
        # select
        sel_list = []
        for index, i in enumerate(self.danmaku_data_raw):
            if (i["timestamp"] - self.live_start_time > start_time) and (
                i["timestamp"] - self.live_start_time < end_time
            ):
                sel_list.append(i)
        self.result_list = sorted(sel_list, key=lambda x: x["timestamp"])
        return self.result_list

    def gene_xml(self, result_path, danmaku_data, clip_start_time=0):
        """
        from danmaku date to xml file
        """
        # TODO add validation to dict data for compatibility
        doc = md.Document()
        node_i = doc.createElement("i")
        doc.appendChild(node_i)
        for node_data in danmaku_data:
            node_d = doc.createElement("d")
            appear_time = (
                int(node_data["timestamp"]) - self.live_start_time - clip_start_time
            ) / 1000
            attr = [
                appear_time,
                node_data["mode"],  # 弹幕类型：滚动，底部
                node_data["font_size"],
                node_data["color"],
                node_data["timestamp"],
                0,
                0,
                0,
            ]
            attr_str = ",".join([str(i) for i in attr])
            node_d.setAttribute("p", attr_str)
            node_msg = doc.createTextNode(node_data["msg"])
            node_d.appendChild(node_msg)
            node_i.appendChild(node_d)
        with open(result_path, "w", encoding="utf-8") as f:
            f.write(doc.toprettyxml(indent="  "))

    def gen_by_video(self, bias=0):
        l = self.get_video_info(bias=bias)
        for index, i in enumerate(l):
            self.gene_xml("./{}.xml".format(index), self.get_danmaku_by_time(*i), i[0])

    def gen_by_list(self, time_list, bias=0):
        l = time_list
        for index, i in enumerate(l):
            self.gene_xml("./{}.xml".format(index), self.get_danmaku_by_time(*i), i[0])


# def proc_bvid(danmaku_file_path, bvid, output_path="./", bias=0):
#     gen_obj = DanmakuGene(danmaku_file_path)
#     video_info = gen_obj.get_video_info_from_web(bvid)
#     sorted_info = sorted(video_info, key=lambda x: x["page"])
#     for ep in sorted_info:
#         ep["duration"] = ep["duration"] * 1000
#     time_ptr = bias
#     for episode in sorted_info:
#         danmaku_list = gen_obj.get_danmaku_by_time(
#             time_ptr, time_ptr + episode["duration"]
#         )
#         gen_obj.gene_xml(
#             "./{}-{}-{}.xml".format(bvid, episode["page"], episode["part"]),
#             danmaku_list,
#             time_ptr,
#         )
#         time_ptr += episode["duration"]

def proc_bvid(danmaku_file_path, bvid, output_path="./", bias=0):
    gen_obj = DanmakuGene(danmaku_file_path)
    video_info = gen_obj.get_video_info_from_web(bvid)
    sorted_info = sorted(video_info, key=lambda x: x["page"])
    for ep in sorted_info:
        ep["duration"] = ep["duration"] * 1000
    time_ptr = bias
    archive_file_name = uuid.uuid1().hex
    with ZipFile("{}/{}".format(output_path, archive_file_name), "w") as f:
        for episode in sorted_info:
            danmaku_list = gen_obj.get_danmaku_by_time(
                time_ptr, time_ptr + episode["duration"]
            )
            file_name = "./{}-{}-{}.xml".format(bvid, episode["page"], episode["part"])
            gen_obj.gene_xml(file_name, danmaku_list, time_ptr)
            time_ptr += episode["duration"]
            f.write(file_name)
            os.remove(file_name)
    return archive_file_name


def test():
    hex = proc_bvid("./test/1605680870.json", "BV1Gz4y1y7wn", "./test")
    print(hex)


if __name__ == "__main__":
    test()
    # get latest file - ssh server "cd danmaku;(ls -1 |tail -1)"
