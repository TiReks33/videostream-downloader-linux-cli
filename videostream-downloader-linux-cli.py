#!/usr/bin/python3

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


HOME = os.path.expanduser("~")
   
DATA_DIR = os.path.dirname(f'{HOME}/__VIDEOSTREAM_DOWNLOADER_OUTPUT__/')

RAW_DATA_DIR = os.path.join(DATA_DIR, "raw")

DOWNLOAD_ERRORS_LOG_F = f'{DATA_DIR}/last_download_errors.log'

def download_chunks(chunklist_url: str, skip_corrupted_snippets=False):
       
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
 
    clear_download_errors_log_file()

    print(">> Downloading chunks files..")
    for i, c in enumerate(url_chunks):
        wget_call_exit_code = os.system(
            "wget --quiet " + " ".join(c) + f" -P {RAW_DATA_DIR} 2>>{DOWNLOAD_ERRORS_LOG_F}"
        )
        if wget_call_exit_code != 0:
            print(_FA+ " wget download of video snippet/s failed.")
            if not skip_corrupted_snippets:
                return False
        else:
            print(_OK+" wget download of video snippet/s successful.")
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

def concatvideos(files_list: list, outputfname: str):   
   
    entries_len=len(files_list)
     
    videolist_tempfname=f'{DATA_DIR}/videolist.txt'
        
    with open(videolist_tempfname,"a") as videolistfile:
        for i in range(entries_len):
                
            fullfpath_command=f"realpath '{files_list[i]}'"#f'realpath {args.concat[i]}'
            get_videofrealpath=subprocess.run(fullfpath_command, capture_output=True, shell=True)
            videofrealpath=get_videofrealpath.stdout.decode('utf-8').strip()
                
            data2append=f"file '{videofrealpath}'"
            videolistfile.write(data2append)
            videolistfile.write("\n")
        
    command2exec=f"ffmpeg -loglevel error -f concat -safe 0 -i '{videolist_tempfname}' -c copy '{DATA_DIR}/{outputfname}.mp4'"
    result=subprocess.run(command2exec, shell=True)
       
    os.remove(videolist_tempfname)

    return result.returncode

def clear_raw() -> None:
    if(os.path.isdir(RAW_DATA_DIR)):
        print('>> Clear existing chunks files dir..')
        shutil.rmtree(RAW_DATA_DIR)

def clear_download_errors_log_file() -> None:
    try:
        os.remove(DOWNLOAD_ERRORS_LOG_F)
    except OSError:
        pass
 

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(prog=_NAME, description=f'::[{_NAME}]:: Downloads input chunklist(.m3u8) of transport stream video by its URL and converts raw fragments to .mp4 video-file')
    main_flags_exclusive_group=parser.add_mutually_exclusive_group(required=True)
    main_flags_exclusive_group.add_argument('-u','--url', help='pass URL of chunklist here',type=str,nargs=1)#,required=True)
    main_flags_exclusive_group.add_argument('-m','--merge', help='flag to only merge existing(in \'raw\' subdir) .ts chunks to .mp4 file without downloading',action='store_true')

    parser.add_argument('-o','--output', help='output .mp4 file name (white-spaces and not-latin characters (4ex., cyrillic etc.) supported)',nargs='+',default=['output_video'])
    parser.add_argument('-d','--download',help='flag to only download chunklist without merging to video-file (will be ignored with \'--merge\' or \'--concat\' flags)',action='store_true')

    parser.add_argument('-a','--allow-failed-snippets',help='this flag skips script terminating after \'wget\' failed to download a (corrupted) videosnippet',action='store_true')
    
    main_flags_exclusive_group.add_argument('-cc','--concat', help='this flag is usefull in situations when you have several already converted(merged) .mp4 videos (4ex., several parts of 1 whole videostream, downloaded and merged via separate chunklists); provide .mp4 file names (parts) paths in input to concat it to 1 video. Note: video parts will be provided to concat in the sequence of arguments.', nargs='+')

    parser.add_argument('-cl','--clear', help='clear chunks folder after converting successfully finished (ignoring if \'--download\' flag is used)',action='store_true')

    args = parser.parse_args()
    
    OUTPUT_NAME=f"{' '.join(args.output)}"

    #concat several videofiles to 1 
    if args.concat:
        print('[Concat existing videos]')
        ccres = concatvideos(args.concat,f'{OUTPUT_NAME}')
        if ccres == 0:
            print(_OK + f" ffmpeg concat to .mp4 successfuly finished. Output: '{DATA_DIR}/{OUTPUT_NAME}.mp4'")
        else:
            print(_FA + f" ffmpeg concat to .mp4 failed.")
        exit()
    

    #if args.download or (not args.download and not args.merge):
    if args.url:
        print('[Download]')
        URL=f"{''.join(args.url)}"
        if not download_chunks(f'{URL}',args.allow_failed_snippets): # if download failed
            print(">> Abort download..")
            if args.clear:
                clear_raw()
            exit()


    if args.merge or (not args.merge and not args.download):
        print('[Merging]')
        if merge2mp4(f'{OUTPUT_NAME}') and args.clear:
            clear_raw()

    print('Done.')



