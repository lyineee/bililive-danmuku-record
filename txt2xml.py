from xml.dom import minidom as md
import json
import os
import cv2
import sys


class DanmakuGene(object):
    danmaku_data_raw = None
    live_start_time = None
    danmaku_data_sorted = None
    result_list = None

    def __init__(self, danmaku_path):
        self.danmaku_path = danmaku_path
        self.video_time_pointer = 0
        self.read_danmaku(self.danmaku_path)

    def read_danmaku(self, path):
        file_name = os.path.splitext(os.path.split(path)[-1])[0]
        self.live_start_time = int(file_name.split('.')[0]+'000')
        self.danmaku_data_raw = []
        with open(path, 'r') as f:
            lines = f.readlines()
            for i in lines:
                self.danmaku_data_raw.append(json.loads(i))

    def get_video_info(self, path='./video', bias=0):
        l = os.listdir(path)
        l.sort(key=lambda x: int(os.path.splitext(x)[0]))
        time_list = [(0, bias)]
        for i in l:
            cap = cv2.VideoCapture(path+'/'+i)
            duration = int((cap.get(7)/cap.get(5))*1000)
            time_list.append((time_list[-1][1], time_list[-1][1]+duration))
        del time_list[0]
        return time_list

    def get_danmaku_by_time(self, start_time, end_time):
        '''
        start_time and end_time unit is minisecond
        '''
        # sort row data
        self.danmaku_data_sorted = sorted(
            self.danmaku_data_raw, key=lambda x: x['timestamp'])
        # select
        start_index = None
        end_index = None
        for index, i in enumerate(self.danmaku_data_sorted):
            if (i['timestamp']-self.live_start_time > start_time) and (start_index is None):
                start_index = index
            if (i['timestamp']-self.live_start_time > end_time) and (end_index is None):
                end_index = index

        self.result_list = self.danmaku_data_sorted[start_index:end_index+1]
        return self.result_list

    def gene_xml(self, result_path, danmaku_data, clip_start_time=0):
        '''
        from danmaku date to xml file
        '''
        doc = md.Document()
        node_i = doc.createElement('i')
        doc.appendChild(node_i)
        for node_data in danmaku_data:
            node_d = doc.createElement('d')
            appear_time = (
                int(node_data['timestamp'])-self.live_start_time-clip_start_time)/1000
            attr = [appear_time, node_data['danmaku.msg_type'], node_data['font_size'],
                    node_data['color'], node_data['timestamp'], 0, 0, 0]
            attr_str = ','.join([str(i) for i in attr])
            node_d.setAttribute('p', attr_str)
            node_msg = doc.createTextNode(node_data['msg'])
            node_d.appendChild(node_msg)
            node_i.appendChild(node_d)
        with open(result_path, 'w', encoding='utf-8') as f:
            f.write(doc.toprettyxml(indent="  "))

    def test(self, bias=0,have_video=False):
        if have_video:
            l = self.get_video_info(bias=bias)
            for index, i in enumerate(l):
                self.gene_xml('./{}.xml'.format(index),
                              self.get_danmaku_by_time(*i), i[0])
        else:
            self.gene_xml('./birthday.xml',self.danmaku_data_raw)


if __name__ == "__main__":
    try:
        bias_time = sys.argv[1]
    except:
        bias_time = 10000
    if not bias_time:
        bias_time = 0
    test = DanmakuGene('./danmaku/1586016056.txt')
    test.test(bias_time,have_video=True)
