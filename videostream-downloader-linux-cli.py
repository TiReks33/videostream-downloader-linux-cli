#!/bin/python3.9

import json
from types import SimpleNamespace
import os
import re
import shutil
import sys
import subprocess
import argparse
import pathlib


_NAME='videostream-downloader-linux-cli'

_OK="[SUCCESS]"

_FA="[FAILED]"

_NOSPACE=">>Not enough disk space in chosen destination.<<"

HOME = os.path.expanduser("~")
   
DATA_DIR = os.path.dirname(f'{HOME}/__VIDEOSTREAM_DOWNLOADER_OUTPUT__/')

RAW_DATA_DIR = os.path.join(DATA_DIR, "raw")

TEMP_DIR = DATA_DIR

DOWNLOAD_ERRORS_LOG_F = f'{DATA_DIR}/last_download_errors.log'

__ext='.mp4'


def get_dir_size(path='.'):
    total = 0
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_dir_size(entry.path)
    return total

def yes_or_no(question):
    reply = str(input(question+' (y/n): ')).lower().strip()
    if reply[:1] == 'y':
        return True
    if reply[:1] == 'n':
        return False
    else:
        return yes_or_no("Please enter y or n.")

def prompt(question):
    return str(input(question + ' ')).lower().strip()

def getFilesInDir(path:str) ->list:
    for file in os.listdir(path):
        if os.path.isfile(os.path.join(path, file)):
            yield file

def download_chunks(chunklist_url: str, skip_corrupted_snippets=False, keep_existing_chunks: bool=False, continue_previous: bool=False):
    
    if keep_existing_chunks :
        print('\'--download-missing-only\' flag activated.')
    elif continue_previous :
        print('\'--continue-interrupted-download\' flag activated.')
 
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

    if keep_existing_chunks : 
        existing_files_in_raw_dir=list(getFilesInDir(RAW_DATA_DIR))
        only_new_chunks_list=list()
        for elem in raw_file_list :
            if elem.split("/")[-1] not in existing_files_in_raw_dir :
                only_new_chunks_list.append(elem)
        raw_file_list=only_new_chunks_list                            

    file_urls = [
        (f if f.startswith("http") else f"{base_url}/{f}") for f in raw_file_list
    ]
    
    file_count=len(raw_file_list)

    if keep_existing_chunks and not file_count :
        print(f'Nothing to download.. All chunks already in {RAW_DATA_DIR}')
        return True;

    url_chunks = []
    for i in range(10):
        start_i = round(i * file_count / 10)
        end_i = min(round((i + 1) * file_count / 10), file_count)
        url_chunks.append(file_urls[start_i:end_i])
    assert sum([len(c) for c in url_chunks]) == file_count


    # download .ts files stage -->>

    if not keep_existing_chunks and not continue_previous :
        # delete old .ts files if exists    
        clear_ts_in_raw_dir()   
 
    clear_download_errors_log_file()

    print(">> Downloading chunks files..")

    add_opt=""

    if continue_previous :
        add_opt="-c"

    for i, c in enumerate(url_chunks):
        urlPortion=" ".join(c)
        # check urls not empty
        if urlPortion.strip() :
             wget_call_exit_code = os.system(
             f"wget {add_opt} --quiet " + urlPortion + f" -P {RAW_DATA_DIR} 2>>{DOWNLOAD_ERRORS_LOG_F}"
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


# if 2 paths similar -> True (slashes will be completely ignored)
def linuxPathsCompare(path1: str, path2: str) -> bool:
    cmpPathsCom=f'[ "$(realpath "{path1}")" = "$(realpath "{path2}")" ]  && echo -n True'
    cmpPathsProc=subprocess.run(cmpPathsCom, capture_output=True, shell=True)
    return True if cmpPathsProc.stdout.decode() == "True" else False    
    
def getMountedVolumeFromPath(path: str) -> str:
    getVolCom=f"echo -n $(df {path} | tail -n1 | awk '{{print $1}}')"
    getVolProc=subprocess.run(getVolCom, capture_output=True, shell=True)
    return getVolProc.stdout.decode()

# result in bytes
def getAvailableSpaceFromPath(path: str) -> int:
    #if _PLATFORM.startswith("freebsd") or _PLATFORM.contains("bsd") :
    getSpaceCom=f"echo -n $(($(df {path} | tail -n1 | awk '{{print $4}}') * 1024))"
    getSpaceProc=subprocess.run(getSpaceCom, capture_output=True, shell=True)
    return int(getSpaceProc.stdout.decode())    


def merge2mp4(title: str, clear_raw: bool=False):

    MERGED_F_FULL_PATH = os.path.join(DATA_DIR, f'{title}{__ext}')

    overwrite_out_file=False

    if not os.path.exists(RAW_DATA_DIR) :
        print(f'{_FA} "raw" data dir with chunks files not found in chosen destination. Exiting..')
        sys.exit(1)
    else :
        if len(os.listdir(RAW_DATA_DIR)) == 0 :
            print(f'{_FA} "raw" data dir is empty. Nothing to merge. Exiting..')
            sys.exit(1)

    if os.path.exists(MERGED_F_FULL_PATH):
        q_text=f"Output filename already exists in chosen destination. Would you like to set another name for output file? If not, existing {__ext} file will be overwritten."                
        if yes_or_no(q_text):
            newName = prompt(f"Please, enter new name for output {__ext} file: ")
            title=newName
            MERGED_F_FULL_PATH = os.path.join(DATA_DIR, f'{title}{__ext}')                            
        else:
            overwrite_out_file=True        
    
    RAW_SIZE=int(get_dir_size(f'{RAW_DATA_DIR}'))

    #AVAILABLE_DISK_SPACE=int(shutil.disk_usage(f'{DATA_DIR}')[2])
    AVAILABLE_DISK_SPACE=getAvailableSpaceFromPath(DATA_DIR)
    AVAILABLE_IN_TEMP=getAvailableSpaceFromPath(TEMP_DIR)

    DATA_VOL=getMountedVolumeFromPath(DATA_DIR)
    TEMP_VOL=getMountedVolumeFromPath(TEMP_DIR)
    RAW_VOL=getMountedVolumeFromPath(RAW_DATA_DIR)

    separateTemp2Data=False

    if DATA_VOL != TEMP_VOL :
        separateTemp2Data=True

    separateRaw2Temp=False

    if RAW_VOL != TEMP_VOL :
        separateRaw2Temp=True

    OP_REQ_SPACE=int(RAW_SIZE)
   
   
    if separateTemp2Data :
        TEMP_REQ=0
        if separateRaw2Temp :
            TEMP_REQ=OP_REQ_SPACE
        else :
            if not clear_raw :
                TEMP_REQ=OP_REQ_SPACE
    
        if AVAILABLE_IN_TEMP < TEMP_REQ :#OP_REQ_SPACE :
            mes=f'{_FA} {_NOSPACE} Free space in temp files folder({TEMP_DIR}, logical device:{TEMP_VOL}): {AVAILABLE_DISK_SPACE}. Approximately required space at least: {OP_REQ_SPACE}.'
            print(mes)
            sys.exit(1)
        if not overwrite_out_file :
            if AVAILABLE_DISK_SPACE < OP_REQ_SPACE :         
                mes=f'{_FA} {_NOSPACE} Free space({DATA_DIR}, logical device:{DATA_VOL}): {AVAILABLE_DISK_SPACE}. Approximately required space at least: {OP_REQ_SPACE}.'
                print(mes)
                sys.exit(1)
      
    else :

        if clear_raw and not separateRaw2Temp :

            if overwrite_out_file :
                OP_REQ_SPACE=0

        else :

            if not overwrite_out_file :
                OP_REQ_SPACE+=OP_REQ_SPACE

        if AVAILABLE_DISK_SPACE < OP_REQ_SPACE :
            mes=f'{_FA} {_NOSPACE} Free space({DATA_DIR}, logical device:{DATA_VOL}): {AVAILABLE_DISK_SPACE}. Approximately required space at least: {OP_REQ_SPACE}.'
            print(mes)
            sys.exit(1)      
  

    print(">> Converting in progress..")

           
    partFilesPathsCom=f"ls -vd {RAW_DATA_DIR}/*.ts $input"
    getPartFilesPaths=subprocess.run(partFilesPathsCom, capture_output=True, shell=True)
    partFilesPaths=getPartFilesPaths.stdout.decode()

    partLis=partFilesPaths.split()
          
    __tfName=f'{title}_temp.ts'

    __tPath = os.path.join(TEMP_DIR, __tfName)

    exit_code=0

    def merge_to_one(_in: list, _out: str, remove_source: bool) -> int :
        retCode=0
        for el in _in :
            shell_com=f'cat {el} >> {_out}'
            if remove_source :
                shell_com+=f';rm {el}'
            retCode = os.system(shell_com)
            if retCode !=0 :
                return retCode
        return 0


    cc_error=f'{_FA} there is error while concat .ts chunks.'

    # simplification for '.ts' output file format
    if __ext == ".ts":

        # case if only 1 .ts file gets merged
        if len(partLis) == 1 :
            print(f"Nothing to merge -- there is only one .ts file already in {RAW_DATA_DIR}.")
            sys.exit(1)

        else :

            exit_code = merge_to_one(partLis,MERGED_F_FULL_PATH,clear_raw)
  
            if exit_code != 0 :
                print(cc_error)
                sys.exit(1)
            
    else :

        # case if only 1 .ts file gets merged
        if len(partLis) == 1 :
            exit_code=concatvideos(partLis,title,overwrite_out_file)
            if clear_raw :
                clear_ts_in_raw_dir()
            
        else :

            exit_code = merge_to_one(partLis,__tPath,clear_raw)
            if exit_code != 0 :
                print(cc_error)
                sys.exit(1)      

            exit_code=concatvideos(__tPath.split(),title,overwrite_out_file)
            
            if exit_code == 0 :
                try:
                    os.remove(__tPath)
                except OSError:
                    pass


    if exit_code == 0:
        print(_OK + f" Merging finished. Output: {MERGED_F_FULL_PATH}")
        return True
    else:
        print(_FA + f" Merging failed.")
        return False


def concatvideos(files_list: list, outputfname: str, overwrite_existing: bool=False):   
   
    entries_len=len(files_list)
     
    videolist_tempfname=f'{DATA_DIR}/videolist.txt'
        
    with open(videolist_tempfname,"a") as videolistfile:
        for i in range(entries_len):
                
            fullfpath_command=f"realpath '{files_list[i]}'"
            get_videofrealpath=subprocess.run(fullfpath_command, capture_output=True, shell=True)
            videofrealpath=get_videofrealpath.stdout.decode('utf-8').strip()
                
            data2append=f"file '{videofrealpath}'"
            videolistfile.write(data2append)
            videolistfile.write("\n")


    command2exec=f"ffmpeg -loglevel error -f concat -safe 0 -i '{videolist_tempfname}' -c copy '{DATA_DIR}/{outputfname}{__ext}'"        
    if overwrite_existing :
        command2exec+=" -y"

    result=subprocess.run(command2exec, shell=True)
       
    os.remove(videolist_tempfname)

    return result.returncode

#def clear_raw() -> None:
#    if(os.path.isdir(RAW_DATA_DIR)):
#        print('>> Clear existing chunks files dir..')
#        shutil.rmtree(RAW_DATA_DIR)


def clear_ts_in_raw_dir() -> None:
    try:
        # Get All List of Files
        for fileName in os.listdir(RAW_DATA_DIR):
            #Check file extension
            if fileName.endswith('.ts'):
                # Remove File
                os.remove(RAW_DATA_DIR + '/' + fileName)
    except OSError:
        pass

def clear_download_errors_log_file() -> None:
    try:
        os.remove(DOWNLOAD_ERRORS_LOG_F)
    except OSError:
        pass
 

if __name__ == "__main__":

    parser = argparse.ArgumentParser(prog=_NAME, description=f'::[{_NAME}]:: Downloads input chunklist(.m3u8) of transport stream video by its URL and converts raw fragments to .mp4 video-file')
    main_flags_exclusive_group=parser.add_mutually_exclusive_group(required=True)
    main_flags_exclusive_group.add_argument('-u','--url', help='pass URL of chunklist here',type=str,nargs=1)
    main_flags_exclusive_group.add_argument('-m','--merge', help='flag to only merge existing(in \'raw\' subdir) .ts chunks to .mp4 file without downloading',action='store_true')

    parser.add_argument('-o','--output', help='output .mp4 file name (white-spaces and not-latin characters (4ex., cyrillic etc.) supported)',nargs='+',default=['output_video'])
    parser.add_argument('-d','--download',help='flag to only download chunklist without merging to video-file (will be ignored with \'--merge\' or \'--concat\' flags)',action='store_true')

    parser.add_argument('-a','--allow-failed-snippets',help='this flag skips script terminating after \'wget\' failed to download a (corrupted) videosnippet',action='store_true')
    
    main_flags_exclusive_group.add_argument('-cc','--concat', help='provide .mp4 file name/s (part/s) path/s to input for concat it to 1 video; this flag is usefull in situations when you have several already converted(merged) .mp4 videos (4ex., several parts of 1 whole videostream, downloaded and merged via separate chunklists). Note: video parts will be provided to concat in the sequence of arguments.', nargs='+')

    parser.add_argument('-cl','--clear', help='clear chunks folder after converting successfully finished (ignoring if \'--download\' flag is used)',action='store_true')

    parser.add_argument('--outputDir', help='replace default output .mp4 file dir by this path', nargs=1,type=str)
    parser.add_argument('--rawDir', help='replace default raw chunks dir by this path', nargs=1,type=str)
    parser.add_argument('--tempDir', help='replace default temporary files dir by this path', nargs=1,type=str)

    download_params_group = parser.add_argument_group('Download raw chunks options','This options group included some [exclusive] parameters for "--download" stage.')
    download_raw_chunks_options_ex_group=download_params_group.add_mutually_exclusive_group(required=False)
    
    download_raw_chunks_options_ex_group.add_argument('--download-missing-only', help='Existing raw .ts files chunks in \'--rawDir\' (if any) will be preserved without rewriting. Note: this method [guarantees] that it\'s only download missing chunks from list, BUT it\'s nothing to do with [partially downloaded] files. Use it if you don\'t care about file integrity/completeness, or you sure of this in advance.',action='store_true')
    
    download_raw_chunks_options_ex_group.add_argument('--continue-interrupted-download', help='Partially downloaded or corrupted raw .ts chunks files of [previous failed/interrupted download] will be re-downloaded from chunks-list (along with missing ones), with replacement of existing. Note: use this method [ONLY] if previous download of chunk-list\'s raw files has been interrupted or failed at some progress stage; otherwise correct output not guaranteed.',action='store_true')

    
    merge_params_group = parser.add_argument_group('Merge options','This options group is for "--merge" stage, and also for \'--concat\' option.')
    merge_params_ex_group=merge_params_group.add_mutually_exclusive_group(required=False)
     
    merge_params_ex_group.add_argument('--ts', help='set this parameter for \'--merge\' stage (or when you use \'--concat\' option), if you want to keep output file in \'.ts\' format without converting to \'.mp4\'.',action='store_true')

    merge_params_ex_group.add_argument('--mkv', help='set this parameter for \'--merge\' stage (or when you use \'--concat\' option), if you want to use \'.mkv\' container format for your output formatting instead of \'.mp4\'.',action='store_true')

    merge_params_ex_group.add_argument('--mov', help='set this parameter for \'--merge\' stage (or when you use \'--concat\' option), if you want to use \'.mov\' container format for your output formatting instead of \'.mp4\'.',action='store_true')

    args = parser.parse_args()
    
    if args.ts:
        __ext='.ts' 
    elif args.mkv:
        __ext='.mkv'
    elif args.mov:
        __ext='.mov'
    #else:
    #    __ext='.mp4'

    OUTPUT_NAME=f"{' '.join(args.output)}" # output .mp4 file name

    if args.outputDir:
        newPath=f"{' '.join(args.outputDir)}" 
        pathlib.Path(newPath).mkdir(parents=True, exist_ok=True) 
        DATA_DIR = newPath
        DOWNLOAD_ERRORS_LOG_F = f'{DATA_DIR}/last_download_errors.log'

    if args.rawDir:
        newPath=f"{' '.join(args.rawDir)}" 
        pathlib.Path(newPath).mkdir(parents=True, exist_ok=True) 
        RAW_DATA_DIR=newPath
        if args.clear :
            if not yes_or_no(f'all existing .ts files in {RAW_DATA_DIR} will be deleted. Continue?'):
                print('Abort..')
                sys.exit(0)

    if args.tempDir:
        newPath=f"{' '.join(args.tempDir)}" 
        pathlib.Path(newPath).mkdir(parents=True, exist_ok=True) 
        TEMP_DIR=newPath
    

    #concat several videofiles to 1 
    if args.concat:
        print('[Concat existing videos]')
        ccres = concatvideos(args.concat,f'{OUTPUT_NAME}',False)
        if ccres == 0:
            print(_OK + f" ffmpeg concat to {__ext} successfuly finished. Output: '{DATA_DIR}/{OUTPUT_NAME}{__ext}'")
        else:
            print(_FA + f" ffmpeg concat to {__ext} failed.")
        exit()
    

    if args.url:
        print('[Download]')
        URL=f"{''.join(args.url)}"
        if not download_chunks(f'{URL}',args.allow_failed_snippets,args.download_missing_only, args.continue_interrupted_download): # if download failed
            print(">> Abort download..")
            if args.clear:
                clear_ts_in_raw_dir()
            exit()


    if args.merge or (not args.merge and not args.download):
        print('[Merging]')
        merge2mp4(f'{OUTPUT_NAME}',args.clear)
     

    print('Done.')



