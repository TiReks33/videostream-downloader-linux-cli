#!/bin/python3

import requests
import sys
import re
from fake_headers import Headers
import shutil
import os

#_OK="[SUCCESS]"

ER_="[ERROR]"

WA_ = "[WARNING]"


try:
    from video_marks import videoMarks
    #HAVE_VMARKS_PKG = True
except ImportError:
    #HAVE_VMARKS_PKG = False
    print(f"{'*'*os.get_terminal_size(fallback=(80,24)).columns}")
    print("pRTB::'video_marks' module is missing.:(")
    print(f"{'*'*os.get_terminal_size(fallback=(80,24)).columns}")


def get_rtb_src(url__: str, pref_qual__: str = None, headers_ = None): 

    marks = videoMarks()

    if pref_qual__ == None:
        pref_qual__ = "SD"

    pref_qual__ = marks.getQuality4romMark(pref_qual__)

    arg_link_id_string =''.join(re.findall(r"video/([a-zA-Z0-9]+)(?:/|)", url__)) # '(?:-|)' -- optional "-" in regexp

    # if NO headers passed (null dict object pointer) -- full 'pack' of request's headers will be generate
    if headers_ == None :
        headers_ = Headers(os="lin", headers=True).generate()

        if headers_.get('Accept-Encoding') != None :
            del headers_['Accept-Encoding'] # 'fix' for random headers to not use special compressions for delivery content (default utf-8) 

    # if dict object pointer is not null, but dict is empty (no headers) -> only basic ('User-Agent' etc.) should be generated for retrieve resource
    elif len(headers_) == 0 :
        headers_ = Headers(os="lin", headers=False).generate()

    print("pRTB::next HTTP headers will be used for GET requests:", headers_)

    response = requests.get(url__, headers=headers_)

    print(f"HTTP GET() response status code: {response.status_code}")

    data = response.text

    f_str = "\"video\":{\"id\":\""
    start_index = data.find(f_str)
    end_index = data.find("\"",start_index + len(f_str))
    vid_id_string = data[(start_index + len(f_str)):end_index]

    if vid_id_string != arg_link_id_string :
        print(f"{WA_} vid_id_string != arg_link_id_string")

    f_str = "\"title\":\""
    start_index = data.find(f_str, end_index)
    end_index = data.find("\"",start_index + len(f_str))
    vid_title_string = data[(start_index + len(f_str)):end_index]

    ext_opt_url="https://rutube.ru/api/play/options/" + arg_link_id_string + "/?no_404=true&referer=https%3A%2F%2Frutube.ru&pver=v2&client=wdp&mq=all"
    print("ext_opt_url==", ext_opt_url)

    opt_response = requests.get(ext_opt_url, headers=headers_)

    print(f"HTTP GET() opt_response status code: {opt_response.status_code}")

    opt_data = opt_response.text


    f_str = "\"m3u8\":\""
    start_index = opt_data.find(f_str)
    end_index = opt_data.find("\"",start_index + len(f_str))
    vid_stream_link_string = opt_data[(start_index + len(f_str)):end_index]

    vid_stream_link_string_cl = vid_stream_link_string.replace('\\u0026', '&')

    print("vid_stream_link clear==", vid_stream_link_string_cl)

    response = requests.get(vid_stream_link_string_cl, headers=headers_)

    print(f"HTTP GET() stream file response status code: {response.status_code}")

    stream_file_data = response.text

    print("stream file data==", stream_file_data)

    def find_all_res(string):
        start = 0
        end = 0
        res_map = {}
        substring = "RESOLUTION="
        while True:
            start = string.find(substring, start)
            if start == -1:
                break
            start += len(substring)
            end = string.find('\n', start)
            key = string[start :end]
            print("key==", key)
            end+=1
            start = string.find('\n', end)

            value = string[end:start]
            print("value==", value)
            res_map[key] = value
        
        return res_map

    res_map = find_all_res(stream_file_data)

    #print("res_map==",res_map)

    q_keys = [ el for el in res_map.keys()]

    #print("keys==", q_keys)    


    closest = marks.get_closest_qual(marks.getRes4romQuality(pref_qual__), q_keys)

    print("closest ==", closest)

    print("res_map[closest]==", res_map[closest])

    return res_map[closest], vid_title_string
    


