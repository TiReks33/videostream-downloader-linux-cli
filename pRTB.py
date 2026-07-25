#!/bin/python3.9

import requests
import sys
import re
from fake_headers import Headers
import shutil
import os

try:
    from video_marks import videoMarks
    #HAVE_VMARKS_PKG = True
except ImportError:
    #HAVE_VMARKS_PKG = False
    print(f"{'*'*os.get_terminal_size().columns}")
    print("pRTB::'video_marks' module is missing.:(")
    print(f"{'*'*os.get_terminal_size().columns}")

http_headers = Headers(os="win", headers=True).generate()

if http_headers.get('Accept-Encoding') != None :
    del http_headers['Accept-Encoding'] # 'fix' for random headers to not use special compressions for delivery content (default utf-8) 


def get_rtb_src(url__: str, pref_qual__: str = None): 

    marks = videoMarks()

    if pref_qual__ == None:
        pref_qual__ = "SD"#marks.getQuality4romMark("SD")

    pref_qual__ = marks.getQuality4romMark(pref_qual__)

    arg_link_id_string =''.join(re.findall(r"video/([a-zA-Z0-9]+)(?:/|)", url__)) # (?:-|) -- optional "-" in regexp


    response = requests.get(url__, headers=http_headers)

    print(f"HTTP GET() response status code: {response.status_code}")

    data = response.text


    f_str = "\"video\":{\"id\":\""
    start_index = data.find(f_str)
    end_index = data.find("\"",start_index + len(f_str))
    vid_id_string = data[(start_index + len(f_str)):end_index]

    if vid_id_string != arg_link_id_string :
        print("[warning]vid_id_string != arg_link_id_string")

    f_str = "\"title\":\""
    start_index = data.find(f_str, end_index)
    end_index = data.find("\"",start_index + len(f_str))
    vid_title_string = data[(start_index + len(f_str)):end_index]


    ext_opt_url="https://rutube.ru/api/play/options/" + arg_link_id_string + "/?no_404=true&referer=https%3A%2F%2Frutube.ru&pver=v2&client=wdp&mq=all"
    print("ext_opt_url==", ext_opt_url)


    opt_response = requests.get(ext_opt_url, headers=http_headers)

    print(f"HTTP GET() opt_response status code: {opt_response.status_code}")

    opt_data = opt_response.text


    f_str = "\"m3u8\":\""
    start_index = opt_data.find(f_str)
    end_index = opt_data.find("\"",start_index + len(f_str))
    vid_stream_link_string = opt_data[(start_index + len(f_str)):end_index]

    vid_stream_link_string_cl = vid_stream_link_string.replace('\\u0026', '&')

    print("vid_stream_link clear==", vid_stream_link_string_cl)

    response = requests.get(vid_stream_link_string_cl, headers=http_headers)

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

    print("res_map==",res_map)

    q_keys = [ el for el in res_map.keys()]

    print("keys==", q_keys)    


    closest = marks.get_closest_qual(marks.getRes4romQuality(pref_qual__), q_keys)

    print("closest ==", closest)

    print("res_map[closest]==", res_map[closest])

    return res_map[closest], vid_title_string
    

if __name__ == "__main__":

    if len(sys.argv) < 2 :
        print("1 arg(url).")
        sys.exit(0)

    url = sys.argv[1]

    qual = None
 
    try:
        qual = sys.argv[2]
    except IndexError: 
        pass

    link, name = get_rtb_src(url, qual)

    print("link==", link, "name==", name)



