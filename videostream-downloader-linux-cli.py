import json
from types import SimpleNamespace
import os
import re
import shutil
import sys
import subprocess
import argparse


# 'macros'
_NAME='videostream-downloader-linux-cli'
# debug
_OK="[SUCCESS]"
_FA="[FAILED]"


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
    
DATA_DIR = os.path.join(PROJECT_DIR, "out")

RAW_DATA_DIR = os.path.join(DATA_DIR, "raw")


def download_chunks(chunklist_url: str):
       
    print(">> Processing..")

    # chunklist
    print(">> Downloading chunklist..")
    chunklist_path = os.path.join(DATA_DIR, chunklist_url.split("/")[-1])
    wget_call_exit_code = os.system(f"wget --quiet {chunklist_url} -P {DATA_DIR}")
    if wget_call_exit_code != 0:
        print(_FA+" Wget download of chunklist failed.")
        return False
    with open(chunklist_path) as f:
        chunklist = f.read()
    os.remove(chunklist_path)

    # download all ts files
    print(">> Grouping chunks..")
    base_url = "/".join(chunklist_url.split("/")[:-1])
    file_pattern = re.compile("[^\n].*\.ts")
    raw_file_list = list(sorted(re.findall(file_pattern, chunklist)))
    file_urls = [
        (f if f.startswith("http") else f"{base_url}/{f}") for f in raw_file_list
    ]
    file_names = list(sorted([f.split("/")[-1] for f in raw_file_list]))
    file_count = len(file_names)
    url_chunks = []
    for i in range(10):
        start_i = round(i * file_count / 10)
        end_i = min(round((i + 1) * file_count / 10), file_count)
        url_chunks.append(file_urls[start_i:end_i])
    assert sum([len(c) for c in url_chunks]) == file_count


    # download all ts files

    # delete old .ts files if exists    
    clear_raw()   
 
    print(">> Downloading chunks files..")
    for i, c in enumerate(url_chunks):
        wget_call_exit_code = os.system(
            "wget --quiet " + " ".join(c) + f" -P {RAW_DATA_DIR}"
        )
        if wget_call_exit_code != 0:
            print(_FA+ " wget download of video snippets failed.")
            return False
        print(f"{(i+1) * 10}% done")
    print(_OK+" Downloading done.")
    return True    

def merge2mp4(title: str):

    MERGED_MP4_FULL_PATH = os.path.join(DATA_DIR, f'{title}.mp4')
    filenames=f"ls -vd {RAW_DATA_DIR}/* $input | tr '\n' '|' | sed '$ s/.$//'"
    outsort=subprocess.run(filenames, capture_output=True, shell=True)
    outsort_res=outsort.stdout.decode()

    # merging all chunks into video-file
    print(">> Converting into mp4..")
    ffmpeg_merge_com=f"ffmpeg -loglevel error -i 'concat:{outsort_res}' -c copy '{MERGED_MP4_FULL_PATH}'"
    ffmpeg_call_exit_code = os.system(ffmpeg_merge_com)

    if ffmpeg_call_exit_code == 0:
        print(_OK + f" Converting finished. Output: {MERGED_MP4_FULL_PATH}")
        return True
    else:
        print(_FA + f" ffmpeg failed.")
        return False

def clear_raw() -> None:
    if(os.path.isdir(RAW_DATA_DIR)):
        print('>> Clear existing chunks files dir..')
        shutil.rmtree(RAW_DATA_DIR)

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(prog=_NAME, description=f'::[{_NAME}]:: Downloads input chunklist(.m3u8) of transport stream video by its URL and converts raw fragments to .mp4 video-file')
    #parser.add_argument('-u','--url', help='pass URL of chunklist here',type=str,nargs=1,required=True)
    required = parser.add_argument_group('required arguments')
    required.add_argument('-u','--url', help='pass URL of chunklist here',type=str,nargs=1,required=True)
    parser.add_argument('-o','--output', help='output .mp4 file name (white-spaces and not-latin characters (4ex., cyrillic etc.) supported)',nargs='+',default=['output_video'])
    part_proc_flags_group=parser.add_mutually_exclusive_group(required=False) # partially processing flags group
    part_proc_flags_group.add_argument('-d','--download',help='flag to only download chunklist without merging to video-file',action='store_true')
    part_proc_flags_group.add_argument('-m','--merge', help='flag to only merge existing .ts data without downloading (URL parameter will be ignored)',action='store_true')
    parser.add_argument('-c','--clear', help='clear chunks folder after converting successfully finished (ignoring if ''--download'' flag is used)',action='store_true')
    args = parser.parse_args()
    
    OUTPUT_NAME=f"{' '.join(args.output)}"
    URL=f"{''.join(args.url)}"

    if args.download or (not args.download and not args.merge):
        print('[Download]')
        if not download_chunks(f'{URL}'):
            print(">> Abort download..")
            if args.clear:
                clear_raw()
            exit()
    if args.merge or (not args.merge and not args.download):
        print('[Merging]')
        if merge2mp4(f'{OUTPUT_NAME}') and args.clear:
            clear_raw()
    print('Done.')



