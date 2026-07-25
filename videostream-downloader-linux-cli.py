#!/bin/python3

_NAME='videostream-downloader-linux-cli'
curVer = "[v0.89b]"

from types import SimpleNamespace
import os
import re
import shutil
import sys
import subprocess
import argparse
import pathlib
from threading import Thread
from enum import Enum, EnumMeta
from argparse import RawTextHelpFormatter
import copy
from multiprocessing.pool import ThreadPool
import time
from aenum import NamedConstant
import threading


try:
    from pRTB import get_rtb_src
    HAVE_RTB_MODULE = True
except ImportError:
    HAVE_RTB_MODULE = False


_D="[DEBUG]"
_SH="[ShellEscape]"

_PLATFORM=sys.platform

_OK="[SUCCESS]"

_FA="[FAILED]"

_WA = "[WARNING]"

LONG_OP = f'{_WA} Please wait while processing operation.. (this may take quite a long time! [Ctrl+C to abort ;)])'                          

_NOSPACE=">>Not enough disk space in chosen destination.<<"

HOME = os.path.expanduser("~")
   
DATA_DIR = os.path.dirname(f'{HOME}/__VIDEOSTREAM_DOWNLOADER_OUTPUT__/')

TEMP_DIR = DATA_DIR

DOWNLOAD_ERRORS_LOG_F = f'{TEMP_DIR}/last_download_errors.log'

__raw_ext='.ts'


def get_pid() -> int :
    return threading.get_native_id()


MAIN_THREAD_PID = get_pid()


def tprint(text : str) -> None :
    prefix = "[MAIN_THREAD] " if get_pid() == MAIN_THREAD_PID else f"[ThreadPID:{get_pid()}] "
    print(prefix + text)


class ext_enum(str, Enum):
    #video
    ##'raw' stream formats
    ts    = 'ts'
    m4s   = 'm4s'
    ##'container' formats
    mkv   = 'mkv'
    mov   = 'mov'
    avi   = 'avi'
    mp4   = 'mp4'

    #audio
    ##'raw' stream formats
    aac   = 'aac'
    ##'container' formats
    mp3   = 'mp3'
    flac  = 'flac'
    wav   = 'wav'

    def __str__(self) -> str:
        return str.__str__(self)


# size in bytes
def get_dir_files_size_amount(path='.',recurs: bool=True):
    total = 0
    with os.scandir(f"{path}") as it:
        for entry in it:
            if entry.is_file():
                total += entry.stat().st_size
            elif recurs and entry.is_dir():   
                total += get_dir_files_size_amount(entry.path,recurs)
    return total



def yes_or_no(question) -> bool :
    reply = str(input(question + " ([Y]es/[N]o): ")).lower().strip()
    if reply == 'y' or reply == 'Y' or reply == 'yes' or reply == 'Yes' or reply == 'YES' :
        return True
    if reply == 'n' or reply == 'N' or reply == 'no' or reply == 'No' or reply == 'NO' :
        return False
    else:
        return yes_or_no("Please, enter 'yes'(y) or 'no'(n)")


class Answer(NamedConstant) :

    # use 'is' operator to distinguish between values
    # with same (duplicate) number (between 'Abort'<->'No' in this case)

    Abort = 0 # = -1 # break/exit/abort etc.
    No = 0 # 'False'
    Yes = 1 # 'True'


def yes_no_abort(question) -> Answer :
    reply = str(input(question + " ([Y]es/[N]o/[A]bort): ")).lower().strip()
    if reply == 'y' or reply == 'Y' or reply == 'yes' or reply == 'Yes' or reply == 'YES' :
        return Answer.Yes
    elif reply == 'n' or reply == 'N' or reply == 'no' or reply == 'No' or reply == 'NO' :
        return Answer.No
    elif reply == 'a' or reply == 'A' or reply == 'abort' or reply == 'Abort' or reply == 'ABORT' :
        return Answer.Abort
    else:
        return yes_no_abort("Please, enter 'yes'(y), 'no'(n) or 'abort'(a)")


def prompt(question):
    return str(input(question + ' ')).lower().strip()

def getFilesInDir(path:str) ->list:
    for file in os.listdir(f'{path}'):
        if os.path.isfile(os.path.join(f'{path}', file)):
            yield file


def shellSpaceEscape(single_entrie: str) -> str :
    return single_entrie.strip().replace("\\","\\\\").replace(' ','\\ ') 


class QuoteType(Enum) :
    Single = 1
    Double = 2

def shellEscape(single_entrie: str, qtype : QuoteType) -> str :
    if qtype == QuoteType.Single :
        return single_entrie.strip().replace("\\","\\\\").replace(' ','\\ ').replace("'","\'").replace('(','\\(').replace(')','\\)')         
    return single_entrie.strip().replace("\\","\\\\").replace(' ','\\ ').replace('"','\"').replace('(','\\(').replace(')','\\)')


# quote string with corresponding quote-symbols escaping 
# (usefull simple solution for filenames/paths arguments
# in shell scripts)
def Quote(text: str, qtype : QuoteType = QuoteType.Double) -> str :
    if qtype == QuoteType.Double :
        return '"' + text.replace('"','\\"') + '"'
    return "'" + text.replace("'","\\'") + "'"         


def remove_fat_ntfs_illegal_chars(str__: str, chars2replace__: str = ' ') -> str:
    fat_ntfs_illegal = ['?','NUL','\\','/',':','*','"','<','>','|']

    tmp_str = str__
    for el in fat_ntfs_illegal:
        tmp_str = tmp_str.replace(el, chars2replace__)
    return tmp_str


def download_chunks(chunklist_url: str, RAW_DATA_DIR: str, skip_corrupted_snippets=False, keep_existing_chunks: bool=False, continue_previous: bool=False) -> bool :

    SRAW_DATA_DIR=shellSpaceEscape(RAW_DATA_DIR) # local (arg) instead of global ..
    SDOWNLOAD_ERRORS_LOG_F=shellSpaceEscape(DOWNLOAD_ERRORS_LOG_F)    

    if keep_existing_chunks :
        print('\'--download-missing-only\' flag activated.')
    elif continue_previous :
        print('\'--continue-interrupted-download\' flag activated.')
 
    tprint(">> Processing..")

    tprint(">> Downloading chunklist..")

    chunklist_f_name = "hls_chunklist" # chunklist_url.split("/")[-1]

    chunklist_f_name = remove_fat_ntfs_illegal_chars(chunklist_f_name)

    chunklist_path = os.path.join(RAW_DATA_DIR, chunklist_f_name)

    downl_chunklist = f"wget '{chunklist_url}' -O {SRAW_DATA_DIR}/{chunklist_f_name}"

    print("wget chunklist command:", downl_chunklist)

    wget_call_exit_code = os.system(downl_chunklist)

    if wget_call_exit_code != 0:
        print(_FA+" Wget download of chunklist failed (is provided URL correct?).")
        return False
    with open(chunklist_path, "r") as f:
        chunklist = f.read()

    remove_file(chunklist_path)


    # download all chunks files
    tprint(">> Grouping chunks..")
    base_url = "/".join(chunklist_url.split("/")[:-1])
    file_pattern = re.compile(f"[^\n].*\\{__raw_ext}")
    raw_file_list = list(sorted(re.findall(file_pattern, chunklist)))


    if keep_existing_chunks : 
        existing_files_in_raw_dir=list(getFilesInDir(RAW_DATA_DIR))
        only_new_chunks_list=list()
        for elem in raw_file_list :
            if elem.split("/")[-1] not in existing_files_in_raw_dir :
                only_new_chunks_list.append(elem)
        raw_file_list=only_new_chunks_list                            



    INIT_F_MARK = "#_init"


    # remove_metadata_init_file_tag
    for ind, substr in enumerate(raw_file_list) :
        #
        # 3.4.13.  EXT-X-MAP (tag, introduced in draft-09 of the HLS spec)
        #
        # The EXT-X-MAP tag specifies how to obtain the Transport Stream PAT/  
        # PMT for the applicable media segment.  It applies to every media 
        # segment that appears after it in the Playlist until the next EXT-X-  
        # DISCONTINUITY tag, or until the end of the playlist. 
        #
        if substr.startswith("#EXT-X-MAP") :
            # Specific pattern
            ch = "=\""

            # Find the index of the pattern
            ch_index = substr.find(ch)

            if ch_index != -1:
                # Get the substring after the character
                t_str = substr[ch_index + 2:]

                # remove leading quote
                raw_file_list[ind] = t_str[:-1] if t_str[-1] == '"' else t_str
                 
                raw_file_list[ind] += INIT_F_MARK #"#_init"


    file_urls = []
    new_content = ""


    clear_el_name = [ f'{SRAW_DATA_DIR}/{elem.split("/")[-1]}' for elem in raw_file_list]


    for indx, elem in enumerate(raw_file_list) :

        if clear_el_name[indx].endswith(INIT_F_MARK) :
            new_n = f'{SRAW_DATA_DIR}/0'
            el_match = f'{new_n}{__raw_ext}'
            duplicate_index = clear_el_name.index(el_match) if el_match in clear_el_name else None
            if duplicate_index is not None :                       
                clear_el_name[duplicate_index] = f'{new_n}b{__raw_ext}'       
                new_n += 'a'                                                
            clear_el_name[indx] = f'{new_n}{__raw_ext}'
            # remove init mark
            raw_file_list[indx] = elem[: - len(INIT_F_MARK)]

            elem = raw_file_list[indx]


        output_fname_append = f' -O "{clear_el_name[indx]}"'
        if elem.startswith("http") :
            new_content = elem + output_fname_append
        else :
            new_content = f"{base_url}/{elem}" + output_fname_append

        file_urls.append(new_content)


    file_count=len(raw_file_list)


    if keep_existing_chunks and not file_count :
        print(f'Nothing to download.. All chunks already in {RAW_DATA_DIR}')
        return True

    url_chunks = []
    for i in range(10):
        start_i = round(i * file_count / 10)
        end_i = min(round((i + 1) * file_count / 10), file_count)
        url_chunks.append(file_urls[start_i:end_i])
    assert sum([len(c) for c in url_chunks]) == file_count


    # download chunks files stage -->>

    if not keep_existing_chunks and not continue_previous :
        # delete old chunks files if exists    
        remove_files(RAW_DATA_DIR,f"{__raw_ext}")   

    # remove downloads log file    
    if pathlib.Path(DOWNLOAD_ERRORS_LOG_F).is_file() :
        # if file exists :
        remove_file(DOWNLOAD_ERRORS_LOG_F) 


    tprint(">> Downloading chunks files..")


    def stprint(ppid2debug : int, text : str) -> None :
        print(f"[Parent:{ppid2debug}]::Sub-threadPID:{get_pid()}] " + text)


    # proceed 1 url portion (portion length determined by input url's portion list
    # size, which, in turn, is determined by chunks amount in input chunklist)
    def url_portion_asynch_proceed(urls_string_list: list, additional_flags4downl: str, silent: bool = False ) -> list :
        
        worker_pid = get_pid()

        # inline "lambda" function for thread exec. :
        # url_portion -- 1 single url to processing
        # list_for_single_int_ret_val -- mutable return (result of single url's processing) by 'reference'
        # silent -- disable debug progress of single url processing..
        def single_url_proceed(url_portion: str, list_for_single_int_ret_val: list, silent: bool = False) -> None :
            ret_ref = list_for_single_int_ret_val # create short reference for result list
            
            nonlocal additional_flags4downl, worker_pid

            tmp_ret_list = []
            
            # check url is not empty
            if url_portion.strip() :
                
                
                wget_call_command = f"wget {additional_flags4downl} --quiet " + url_portion + f" 2>>{SDOWNLOAD_ERRORS_LOG_F}"


                wget_call_exit_code = os.system(
                    wget_call_command
                )


                if wget_call_exit_code != 0 :
                    if not silent :
                        stprint(worker_pid, _FA + " there are error while video snippet download.")
                    
                    tmp_ret_list = [int(-1)]
                
                else :
                    if not silent :
                        stprint(worker_pid, _OK + " download of video snippet successful.")
                    tmp_ret_list = [int(1)]
                
            else :
                if not silent :
                    stprint(worker_pid, "{_D} snippet is empty, nothing to proceed.")
                tmp_ret_list = [int(0)]
            
            
            if ret_ref is not None :

                ret_ref.append(tmp_ret_list[0])

            return None
        #defend


        #print(_D + " Current worker thread PID: " + str(worker_pid))
        tprint(_D + " Sub-threads number to be executed: " + str(len(urls_string_list)))


        threads = [None] * len(urls_string_list)
        results = []#[None] * len(urls_string_list)

        for i, el in enumerate (urls_string_list) :

            threads[i] = Thread(target = single_url_proceed, args=(el, results, silent))
            threads[i].start()
        
        # running threads processing (join)
        for thr_el in threads :
            thr_el.join()

        ## threads execution results transfer

        return results

    # defend

    
    add_opt=""

    if continue_previous :
        add_opt="-c"


    # portions of urls enumerate, for partially execute them in threads
    for i, c in enumerate(url_chunks) :
              
        # check urls portion is not empty
        if (' '.join(c)).strip() :


            results_from_asynch_proceed = url_portion_asynch_proceed(c, add_opt, False)

       
            if -1 in results_from_asynch_proceed :
                tprint(_FA+ " wget download of video snippets portion ended with an error/s.")
                if not skip_corrupted_snippets:
                    return False
            else:

                tprint(_OK+" wget download of video snippets portion successful.")

        else :

            tprint("{_D} urls list is empty, nothing to proceed.")



        tprint(f"{(i+1) * 10}% done")
    
    tprint(_OK + " Downloading done.")
     
    return True    



def getFileSize(fpath: str) -> int:
    if os.path.isfile(f"{fpath}") :
        return os.path.getsize(f"{fpath}")
    else :
        return -1

# if 2 paths similar -> True (slashes will be completely ignored)
def linuxPathsCompare(path1: str, path2: str) -> bool:
    cmpPathsCom=f'[ "$(realpath "{path1}")" = "$(realpath "{path2}")" ]  && echo -n True'
    cmpPathsProc=subprocess.run(cmpPathsCom, capture_output=True, shell=True)
    return True if cmpPathsProc.stdout.decode() == "True" else False    
    
def getMountedVolumeFromPath(path: str) -> str:
    getVolCom=f"echo -n $(df '{path}' | tail -n1 | awk '{{print $1}}')"
    getVolProc=subprocess.run(getVolCom, capture_output=True, shell=True)
    return getVolProc.stdout.decode()

# result in bytes
def getAvailableSpaceFromPath(path: str) -> int:
    getSpaceCom=""
    if _PLATFORM.startswith("freebsd") or "bsd" in _PLATFORM :
        # GB (not GiB)
        getSpaceCom=f"echo -n $(( $(BLOCKSIZE=1000 df '{path}' | tail -n1 | awk '{{print $4}}') * 1000 ))"
    else :
        getSpaceCom=f"echo -n $(df -B 1 '{path}' | tail -n1 | awk '{{print $4}}')"
    getSpaceProc=subprocess.run(getSpaceCom, capture_output=True, shell=True)
    return int(getSpaceProc.stdout.decode())    


# old 'merge2mp4'
def merge2output_format(title: str, __ext: str, RAW_DATA_DIR: str, clear_raw: bool=False, overwrite_out_file: bool = False) -> bool :

    print("DATA_DIR==", DATA_DIR)
    print("RAW_DATA_DIR==", RAW_DATA_DIR)
    print("TEMP_DIR==", TEMP_DIR)

    stitle=shellSpaceEscape(title)
    SDATA_DIR=shellSpaceEscape(DATA_DIR)
    SRAW_DATA_DIR=shellSpaceEscape(RAW_DATA_DIR) # local (arg) instead of global..
    STEMP_DIR=shellSpaceEscape(TEMP_DIR)

    MERGED_F_FULL_PATH = os.path.join(DATA_DIR, f'{title}{__ext}')
    SMERGED_F_FULL_PATH = shellSpaceEscape(MERGED_F_FULL_PATH)


    if not os.path.exists(f"{RAW_DATA_DIR}") :
        print(f'{_FA} "raw" data dir with chunks files not found in chosen destination. Exiting..')

        return False
    else :
        if len(os.listdir(f"{RAW_DATA_DIR}")) == 0 :
            print(f'{_FA} "raw" data dir is empty. Nothing to merge. Exiting..')

            return False


    if overwrite_out_file == False :

        if os.path.exists(f"{MERGED_F_FULL_PATH}"):
            q_text=f"Output file (name: '{title}', extension: '{__ext}') already exists in chosen destination. Would you like " \
                f"to set another name for output file? If not, existing '{__ext}' file will be overwritten."

            answ = yes_no_abort(q_text)

            if answ :
                newName = prompt(f"Please, enter new name for output '{__ext}' file: ")
                title=newName
                stitle=shellSpaceEscape(newName)
                MERGED_F_FULL_PATH = os.path.join(SDATA_DIR, f'{title}{__ext}')
                SMERGED_F_FULL_PATH=shellSpaceEscape(MERGED_F_FULL_PATH)
            elif answ is Answer.Abort :
                print("Aborting..")
                return False
            else :
                overwrite_out_file=True
 

    RAW_SIZE=int(get_dir_files_size_amount(f'{RAW_DATA_DIR}'))

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
    
        if AVAILABLE_IN_TEMP < TEMP_REQ :
            mes=f'{_FA} {_NOSPACE} Free space in temp files folder({TEMP_DIR}, ' \
                f'logical device:{TEMP_VOL}): {AVAILABLE_IN_TEMP}. Approximately required space at least: {TEMP_REQ}.' #{OP_REQ_SPACE}.'
                #f'logical device:{TEMP_VOL}): {AVAILABLE_DISK_SPACE}. Approximately required space at least: {TEMP_REQ}.' #{OP_REQ_SPACE}.'
            print(mes)

            return False
        if overwrite_out_file : 
            OP_REQ_SPACE  = OP_REQ_SPACE - getFileSize(MERGED_F_FULL_PATH) 
        if AVAILABLE_DISK_SPACE < OP_REQ_SPACE :         
            mes=f'{_FA} {_NOSPACE} Free space({DATA_DIR}, logical device:{DATA_VOL}): ' \
                f'{AVAILABLE_DISK_SPACE}. Approximately required space at least: {OP_REQ_SPACE}.'
            print(mes)
            #sys.exit(1)
            return False
      
    else :

        if clear_raw and not separateRaw2Temp :

            if __ext == __raw_ext :
                OP_REQ_SPACE=0
            elif overwrite_out_file :
                OP_REQ_SPACE = OP_REQ_SPACE - getFileSize(MERGED_F_FULL_PATH)

        else :

            if overwrite_out_file and __ext == __raw_ext : 
                OP_REQ_SPACE = OP_REQ_SPACE - getFileSize(MERGED_F_FULL_PATH)
            elif overwrite_out_file and __ext != __raw_ext :
                OP_REQ_SPACE += (OP_REQ_SPACE - getFileSize(MERGED_F_FULL_PATH))
            elif not overwrite_out_file and __ext != __raw_ext :
                OP_REQ_SPACE += OP_REQ_SPACE 


        if AVAILABLE_DISK_SPACE < OP_REQ_SPACE :
            mes=f'{_FA} {_NOSPACE} Free space({DATA_DIR}, logical device:{DATA_VOL}): ' \
                f'{AVAILABLE_DISK_SPACE}. Approximately required space at least: {OP_REQ_SPACE}.'
            print(mes)

            return False
  

    tprint(">> Converting in progress (merging stage)..")
    
    
    partFilesPathsCom=f"ls -vd {SRAW_DATA_DIR}/*{__raw_ext}"
    getPartFilesPaths=subprocess.run(partFilesPathsCom, capture_output=True, shell=True)
    partFilesPaths=getPartFilesPaths.stdout.decode()
    
    partLis=partFilesPaths.split('\n')[:-1]

    __tfName=f'{title}_temp{__raw_ext}'

    __tPath = os.path.join(TEMP_DIR, __tfName)
    

    # 'shell' concat (with 'dynamic' rm(remove) while concat process continious)
    def merge_to_one(_in: list, _out: str, remove_source: bool) -> bool :

        for el in _in :
            shell_com=f'cat "{el}" >> "{_out}"'
            if remove_source :
                shell_com+=f';rm "{el}"'
            retCode = os.system(shell_com)
            if retCode != 0 :
                return False
        return True
    #defend


    exit_result = False

    cc_error=f'{_FA} there is error while merging chunks.'

    # simplification for raw output file format
    if __ext == __raw_ext:

        # case if only 1 raw file gets merged
        if len(partLis) == 1 :
            print(f"Nothing to merge -- there is only one {__raw_ext} file already in {RAW_DATA_DIR}.")

            return True

        else :

            if overwrite_out_file :
                remove_file(MERGED_F_FULL_PATH)

            exit_result = merge_to_one(partLis,MERGED_F_FULL_PATH,clear_raw)
  
            if exit_result == False :
                print(cc_error)

            
    else :

        # case if only 1 raw file gets merged
        if len(partLis) == 1 :

            exit_result = concatvideos(partLis,title, __ext, overwrite_out_file, clear_raw)

            
        else :


            exit_result = merge_to_one(partLis,__tPath,clear_raw)
            if exit_result == False :
                print(cc_error)

                return False


            exit_result=concatvideos([__tPath],title, __ext, overwrite_out_file,True)


    if exit_result == True:
        print(_OK + f" Merging finished. Output: '{MERGED_F_FULL_PATH}'")
        return True
    else:
        print(_FA + f" Merging failed.")
        return False




# this doesn't fit when you need to concat several videofiles -- output will be, 4ex., audiotrack from 1 file, and video sequence from another..;
# only useful when overlaying audio onto video part; one onto another
# Note: if function called NOT from Shell, files_list argument must contain PATHS (relative or full) not just filenames..
def concatvideos_filter(files_list: list, outputfname: str, __ext: str, overwrite_existing: bool=False, delete_source_after: bool = False) -> bool :

    entries_len=len(files_list)

    cc_prot_list = []

    for el in files_list :

        fullfpath_command=f'realpath {Quote(el)}' #// need double quotes escape

        get_videofrealpath=subprocess.run(fullfpath_command, capture_output=True, shell=True)
        videofrealpath=get_videofrealpath.stdout.decode('utf-8').strip()

        cc_prot_list.append(f'{Quote(videofrealpath)}')        


    cc_prot_list_str = ' -i '.join(cc_prot_list)


    OUTP = Quote(f'{DATA_DIR}/{outputfname}{__ext}')


    command2exec=f"ffmpeg -loglevel error -i {cc_prot_list_str} -c copy {OUTP}"        


    if overwrite_existing :
        command2exec+=" -y"

    result=subprocess.run(command2exec, shell=True)
   


    if result.returncode == 0 :
        if delete_source_after :
            for source_file in files_list:
                 remove_file(source_file)
        return True
    return False

#defend



# ffmpeg concat demuxer
def concatvideos(files_list: list, outputfname: str, __ext: str, overwrite_existing: bool=False, delete_source_after: bool = False) ->bool :

    entries_len=len(files_list)


    videolist_tempfname=f'{DATA_DIR}/videolist.txt'    

    with open(videolist_tempfname,"a") as videolistfile:
        for el in files_list :
            fullfpath_command=f"realpath {Quote(el)}"
            get_videofrealpath=subprocess.run(fullfpath_command, capture_output=True, shell=True)
            videofrealpath=get_videofrealpath.stdout.decode('utf-8').strip()


            # From ffmpeg docs: The quote character ' itself cannot be quoted, so 
            # you may need to close the quote and escape it.
            quoted4demux_file = '\'' + videofrealpath.replace("'","'\\''") + '\''
            data2append = f'file {quoted4demux_file}'
            videolistfile.write(data2append)
            videolistfile.write("\n")



    OUTP = Quote(f'{DATA_DIR}/{outputfname}{__ext}')

    # concat "demuxer"
    command2exec=f"ffmpeg -loglevel error -f concat -safe 0 -i {Quote(videolist_tempfname)} -c copy {OUTP}"        
    if overwrite_existing :
        command2exec+=" -y"

    result=subprocess.run(command2exec, shell=True)
   
    remove_file(videolist_tempfname)    



    if result.returncode == 0 :
        if delete_source_after :
            for source_file in files_list:
                 remove_file(source_file)
        return True
    return False

#defend



def ffmpeg_convert(inp_file_path: str, outputfname: str, __ext: str, overwrite_existing: bool = False, delete_source_after: bool = False, reencoding: bool = False) -> bool :

    OUTP = Quote(f'{DATA_DIR}/{outputfname}{__ext}')

    command2exec = ""
    if not reencoding :
        command2exec=f"ffmpeg -loglevel error -i {Quote(inp_file_path)} -c copy {OUTP}"        
    else :
        command2exec=f"ffmpeg -loglevel error -i {Quote(inp_file_path)} {OUTP}"        
    
    if overwrite_existing :
        command2exec+=" -y"

    result=subprocess.run(command2exec, shell=True)
  

    if result.returncode == 0 :
        if delete_source_after :
            remove_file(inp_file_path)
        return True
    return False
#defend



# remove single file
def remove_file(FPATH: str) -> None:
    try:
        if os.path.exists(FPATH):
            os.remove(FPATH)
    except OSError as e:
        print(f"remove_file(..)::Error while removing file: '{FPATH}'. Error descr.: '{e}'.")
        pass
#defend


# remove files from specific directory (with specific extension pattern)
def remove_files(DIR: str, EXT: str) -> None:
    try:
        # Get All List of Files
        for fileName in os.listdir(DIR):
            #Check file extension
            if fileName.endswith(EXT):
                # Remove File
                os.remove(DIR + '/' + fileName)
    except OSError as e:
        print(f"remove_files(..)::Error while removing files with extension '.{EXT}' from dir: '{DIR}'. Error descr.: '{e}'.")
        pass
#defend


def get_curr_output_format(args: argparse.Namespace) -> str :
    args_dict = vars(args)
    for arg_ in args_dict :
        for el in ext_enum :
            if str(arg_) == str(el) :#.value) :
                if args_dict[arg_] :
                    return str(el.value)

    return ""
#defend


def change_curr_output_format(args: argparse.Namespace, new_format: ext_enum) :

#    for ind, fel in enumerate (ext_enum) :
#        print(f"[[{ind}] format{{{fel}}}:", vars(args)[fel], end="\n")

    ol_format = get_curr_output_format(args)

    vars(args)[new_format] = True

    if ol_format in vars(args) :
        vars(args)[ol_format] = False

#    for ind, fel in enumerate (ext_enum) :
#        print(f"[[{ind}] format{{{fel}}}:", vars(args)[fel], end="\n")

#defend



def check_file_is_video(filepath: str) -> bool :

    file2check = filepath#Quote(filepath)

    ffprobe_get_codec_type = str(f"ffprobe -v error -select_streams v:0 \
    -show_entries stream=codec_type -of default=noprint_wrappers=1:nokey=1").split() + [file2check]
    result = subprocess.run(ffprobe_get_codec_type, capture_output=True)
    print("FFPROBE GET CODEC TYPE: " + result.stdout.decode().strip() + ';')

    if result.returncode == 0 :
        if result.stdout.decode().strip() == "video" :
            ffprobe_count_frames = str("ffprobe -v error -select_streams v:0 \
            -count_packets -show_entries stream=nb_read_packets -of csv=p=0").split() + [file2check]
            result = subprocess.run(ffprobe_count_frames, capture_output=True)
            print("FFPROBE FRAMES AMOUNT: " + result.stdout.decode().strip() + ';')

            if result.returncode == 0 :
                if int(result.stdout.decode().strip()) > 1 :
                    print(f"{filepath} -- this is video!!")
                    return True

    return False
#defend


def check_chunklist_url_contains_video(chunklist_url: str) -> bool :

    processed_arg = chunklist_url

    chunklist2check = os.path.splitext(processed_arg)

    if len(chunklist2check) > 1 and chunklist2check[1] != ".m3u8" :
        print("sorry, argument is not a chunklist's URL..")
        return False

    ffprobe_get_codec_type = str(f"ffprobe -loglevel error -show_entries \
    stream=codec_type -of csv=p=0").split() + [processed_arg]
    result = subprocess.run(ffprobe_get_codec_type, capture_output=True)

    if result.returncode == 0 :
        res_lis = result.stdout.decode().strip().split()
        if len(res_lis) == 2 and res_lis[0] == "video" and res_lis[1] == "video" :
            print(f"{chunklist_url} -- is a video chunklist's URL!!")
            return True

    return False
#defend


def check_file_is_audio(filepath: str) -> bool :

    file2check = filepath#Quote(filepath)

    ffprobe_get_codec_type = str(f"ffprobe -loglevel error -show_entries \
    stream=codec_type -of csv=p=0").split() + [file2check]
    result = subprocess.run(ffprobe_get_codec_type, capture_output=True)
    print("FFPROBE GET CODEC TYPE: ",result.stdout.decode().strip().split(),';')
    print(type(result.stdout))

    if result.returncode == 0 :
        res = result.stdout.decode().strip()
        if len(res.split()) == 1 and res == "audio" :
            print(f"{filepath} -- this is audio!!")
            return True


    return False
#defend


def check_chunklist_url_contains_audio(chunklist_url: str) -> bool :

    processed_arg = chunklist_url

    chunklist2check = os.path.splitext(processed_arg)

    if len(chunklist2check) > 1 and chunklist2check[1] != ".m3u8" :
        print("sorry, argument is not a chunklist's URL..")
        return False

    ffprobe_get_codec_type = str(f"ffprobe -loglevel error -show_entries \
    stream=codec_type -of csv=p=0").split() + [processed_arg]
    result = subprocess.run(ffprobe_get_codec_type, capture_output=True)

    if result.returncode == 0 :
        res_lis = result.stdout.decode().strip().split()
        if len(res_lis) == 2 and res_lis[0] == "audio" and res_lis[1] == "audio" :
            print(f"{chunklist_url} -- is a audio chunklist's URL!!")
            return True


    return False
#defend


def get_rtb_link(url__ : str, pref_qual__: str = None) :
    
    link, name = get_rtb_src(url__, pref_qual__)
    
    name = remove_fat_ntfs_illegal_chars(name, '_')

    print("get_rtb_link(..)::extracted link:", link)
    print("get_rtb_link(..)::extracted name:", name)

    return link, name


def get_args() -> argparse.Namespace :

    parser = argparse.ArgumentParser(prog=_NAME, description=f'::[{_NAME + curVer}]:: Downloads input ' \
        f'chunklist(.m3u8) of transport stream video by its URL and converts raw fragments to \'.mp4\' (or ' \
            f'other available format) file. Also suitable for audio streams.', epilog = '[Hint]: if result of \'--concat\' or \'--tracks-overlay\' ' \
                f'operation is NOT successful, or output result is not in satisfied state, it may be helpful to convert ' \
                    f'input file argument/s to another suitable format first, depending on the context. This can be reached by ' \
                        f'executing a program with \'--convert\' parameter; list of available output formats shown upper above (default ' \
                            f'is \'.mp4\' (\'--mp4\' parameter)).\nHave a good day fella!:)', formatter_class = RawTextHelpFormatter)

    main_flags_exclusive_group = parser.add_mutually_exclusive_group(required=True)
    
    main_flags_exclusive_group.add_argument('-v','--version', help=f'Get current version of \'{_NAME}\'',action='store_true')


    main_flags_exclusive_group.add_argument('-u','--url', help='pass URL of chunklist here',type=str,nargs='+')

    #
    main_flags_exclusive_group.add_argument('-rtb','--rutube', help='resolve URL of resource. Takes 2 parameters: 1) resource url (to resolve it to .m3u8 link), 2) preffered video quality (\'480p\',\'720p\', etc.).', nargs=2,type=str);
    #

    main_flags_exclusive_group.add_argument('-m','--merge', help='flag to only merge existing (in \'--rawDir\' directory) chunks to output formatted file, without downloading',action='store_true')

    parser.add_argument('-o','--output', help='output file name (white-spaces and not-latin characters (4ex., cyrillic etc.) supported)',nargs='+',default=None)#['output_file'])
    parser.add_argument('-d','--download',help='flag to only download chunklist, without merging to output file afterwards (works only with \'--url\' flag, will be ignored otherwise)',action='store_true')

    download_params_group = parser.add_argument_group('Download raw chunks options','This options group included some [exclusive] parameters for "--download" stage.')
    download_raw_chunks_options_ex_group=download_params_group.add_mutually_exclusive_group(required=False)
    
    download_raw_chunks_options_ex_group.add_argument('--download-missing-only', help='Existing raw files chunks in \'--rawDir\' (if any) will be preserved without rewriting. [Note]: this method [guarantees] that it\'s only download missing chunks from list, BUT it\'s nothing to do with [partially downloaded] files. Use it if you don\'t care about file integrity/completeness, or you sure of this in advance.',action='store_true')
    
    download_raw_chunks_options_ex_group.add_argument('--continue-interrupted-download', help='Partially downloaded or corrupted raw chunks files of [previous failed/interrupted download] will be re-downloaded from chunks-list (along with missing ones), with replacement of existing. [Note]: use this method [ONLY] if previous download of chunk-list\'s raw files has been interrupted or failed at some progress stage; otherwise correct output not guaranteed.',action='store_true')


    parser.add_argument('-a','--allow-failed-snippets',help='this flag skips script terminating after \'wget\' downloading errors',action='store_true')
    
    parser.add_argument('--customRaw',help='custom format extension for raw chunks instead of \'.ts\' (4ex., \'.aac\' audio stream parts).', nargs=1,type=str);

    main_flags_exclusive_group.add_argument('-cc','--concat', help='provide file/s (part/s) path/s to input for concat it to 1 monolitic file; this flag is usefull in situations when you have several already converted(merged) files (4ex., several parts of 1 whole videostream, downloaded and merged via separate chunklists). [Note]: video parts will be provided to concat in the sequence of arguments.', nargs='+')

    # overlaying -- "наложение" треков (<-- cyrillic)
    main_flags_exclusive_group.add_argument('-t','--tracks-overlay', help='provide file/s (part/s) path/s of track/s for overlaying them 1 on 1; this flag can be usefull in situations when you have 2 separate parts of 1 media entity (4ex., audio- and video- separated parts of \'.m4s\' video), and you need to unite them to 1 monolitic file (with one-on-one overlay).', nargs=2)

    
    main_flags_exclusive_group.add_argument('--convert', help='provide input file to convert to specific output format via ffmpeg (format can be specified by \'--{format}\' flag (see \'--help\' for all available formats list).', nargs=1)
    

    convert_flags = parser.add_argument_group('Convert additional flags group','This group included some flags for "--convert" parameter.')
    
    convert_flags.add_argument('--reencode', help='If this flag is set, output file\'s audio/video frames will be reencoded (quality of output video/audio may be differ than source). [Note]: this much longer operation then copying existing frames from input source; more rational use of this is only in case if execution of \'--convert\' without this flag gives output file of specified format not in satisfying state (4ex., video sequence of output is freezes/in low frame rate etc.).',action='store_true')
    

    parser.add_argument('-cl','--clear', help='this flag is context-depended: in \'--merge\' stage: clearing chunks folder after converting successfully finished; with \'--concat\', \'--tracks_overlay\' or \'--convert\': deleting source files IF operation execution was successful; ignoring if \'--download\' flag is used.',action='store_true')

    parser.add_argument('--outputDir', help='replace default output .mp4 file dir by this path', nargs=1,type=str)
    parser.add_argument('--rawDir', help='replace default raw chunks dir by this path', nargs=1,type=str)
    parser.add_argument('--tempDir', help='replace default temporary files dir by this path', nargs=1,type=str)
    
    # spaghetti is so delicious!:)
    
    merge_params_group = parser.add_argument_group('Output formats','This options group is for \'--merge\' stage, and also for \'--concat\', \'--tracks-overlay\', \'--convert\' options; specify output data formatting (default is \'.mp4\').')
    merge_params_ex_group=merge_params_group.add_mutually_exclusive_group(required=False)


    for el in ext_enum :
        merge_params_ex_group.add_argument(f'--{el}', help=f'set this parameter if you want to use \'.{el}\' format for your output data.',action='store_true', default=False)#bool_)


    parser.add_argument('-y','--yes-please',help=f'"Technical" flag. This flag is for skipping (automaticly confirming) question dialogs (4ex., about overwriting directory). \
    {_WA}: if this flag is set, You will lose the possibility to rename a file if it already exists; it will be forcibly replaced.',action='store_true')


    # parse args
    args = parser.parse_args() #type:->argparse.Namespace

    # set defaults..
    curr_format = get_curr_output_format(args)

    if(curr_format == "") :
        # if no format passed via arguments, default is .mp4
        change_curr_output_format(args, ext_enum.mp4)

    curr_format = get_curr_output_format(args)


    return args
#defend




def main_logic (args: argparse.Namespace) -> int :
    
    # '__ext' mustn't be a global var????????????????????????????????????????
    global DATA_DIR, __raw_ext, TEMP_DIR##, RAW_DATA_DIR


    __ext = '.' + get_curr_output_format(args)


    RAW_DATA_DIR = os.path.join(DATA_DIR, "raw")

    if args.customRaw:
        temp_ext = f"{' '.join(args.customRaw)}".strip()
        if temp_ext != "" :
            if not temp_ext.startswith('.') :
                temp_ext = '.' + temp_ext
            elif temp_ext == "." or temp_ext == ".." :
                temp_ext = ""
        __raw_ext = temp_ext


    rawDirPathExists = False

    if args.rawDir:
        newPath=f"{' '.join(args.rawDir)}"

        Path_ = pathlib.Path(newPath)

        rawDirPathExists = Path_.exists()

        Path_.mkdir(parents=True, exist_ok=True)

        RAW_DATA_DIR=newPath

    else : # default RawDir
        Path_ = pathlib.Path(RAW_DATA_DIR)

        rawDirPathExists = Path_.exists()

        Path_.mkdir(parents=True, exist_ok=True)


    if not os.path.exists(DATA_DIR) :
        os.makedirs(DATA_DIR)


    if args.outputDir:
        newPath=f"{' '.join(args.outputDir)}" 
        pathlib.Path(newPath).mkdir(parents=True, exist_ok=True) 
        DATA_DIR = newPath


    if args.tempDir:
        newPath=f"{' '.join(args.tempDir)}"
        pathlib.Path(newPath).mkdir(parents=True, exist_ok=True) 
        TEMP_DIR=newPath
        DOWNLOAD_ERRORS_LOG_F = f'{TEMP_DIR}/last_download_errors.log'


    if not args.yes_please :

        if ((args.clear and args.merge) or (((args.url or args.rutube) and (not args.download or (args.download and not args.continue_interrupted_download and not args.download_missing_only))) and rawDirPathExists)) :
            print('')
            if not yes_or_no(f'{_WA} all existing chunks (\'{__raw_ext}\') files in \'{RAW_DATA_DIR}\' (if any) will be deleted. Continue?'):
                print('Abort..')

                return False

        elif ((args.clear and args.concat) or (args.clear and args.tracks_overlay) or (args.clear and args.convert)) :
            print('')
            if not yes_or_no(f'{_WA} Source files will be deleted after successful end of operation. Continue?'):
                print('Abort..')

                return False


    # for more than 2 args to '--url' (recursion)..
    if args.url :
        url_amount = len(args.url)
       
        if url_amount > 2 :
            print("'--url' flag expects no more than two arguments. Abort..")

            return False
        elif url_amount == 2:

            if __raw_ext != ".m4s" :
                print(f"{_FA} '--url' parameter currently ({curVer}) supports 2 arguments " \
                        f"(for download && merging video and audio stream's parts asynchronously) " \
                            f"ONLY for fragmented MP4 HLS (additional parameter '--customRaw=m4s' " \
                                f"pass required).")
                return False

            # recursion for 2 '.m4s' links (asynchronous download and
            # processing for audio and video parts)
            else : # IS '.m4s' files chunklist

                pool = ThreadPool(processes=len(args.url))

                pool_args_list = []

                output_names = []

                for ind, el in enumerate (args.url) :
                    # arguments for threads
                    temp_args = copy.copy(args)
                    temp_args.url = [el]
                    temp_args.rawDir = [ str(os.path.join(RAW_DATA_DIR, str(ind))) ]
                    change_curr_output_format(temp_args, ext_enum.m4s)

                    t_outp_name_str = f"{' '.join(args.output)}" + str(ind)

                    #if not args.download :
                    temp_args.output = [t_outp_name_str]


                    output_names += [ os.path.join(DATA_DIR, t_outp_name_str) + __raw_ext ]

                    temp_args.yes_please = True # skip all dialog boxes when file/s exists

                    pool_args_list += [(temp_args,)]

                with ThreadPool(processes = len(args.url)) as pool :
                    results = pool.starmap(main_logic, pool_args_list)

                    pool.close()
                    pool.join()

                # all threads finished successfuly
                if False not in results :
                    tprint(f"{_OK} All threads returned successful results!")
                # all threads returned failed results
                if True not in results :
                    tprint(f"{_FA} All threads returned failed results")
                # some threads (not all) return failed results
                elif False in results :
                    tprint(f"{_WA} Oops, not all threads returned results are good..")


                if not args.download :
                    args.tracks_overlay = output_names
                    args.url = False 
                    
                    ret = main_logic(args)
                     
                    return ret

                return True



    if args.url or args.merge :
        tprint(f'Specified raw videostream chunks format -> \'{__raw_ext}\'')
    
    if not args.download :
        tprint(f'Specified output file format -> \'{__ext}\'')

    
    is_output_name_dflt = False
    if args.output is None :
        OUTPUT_NAME = 'output_file'
        is_output_name_dflt=True
    else:
        OUTPUT_NAME=f"{' '.join(args.output)}" # output file name


    #concat several videofiles to 1 
    if args.concat:
        print('[Concat existing videos]')

        cc_args = ':::::::::::::'.join(args.concat)#.strip('"')
        
        print(args.concat)
        print(f"{_D} cc_args::" + cc_args + ';')
        
        ccres = concatvideos(args.concat, f'{OUTPUT_NAME}', __ext, args.yes_please, args.clear) #False, args.clear)
        if ccres == True:
            print(_OK + f" ffmpeg concat to '{__ext}' successfuly finished. Output: '{DATA_DIR}/{OUTPUT_NAME}{__ext}'")

        else:
            msg_postfix = ""
            if args.clear :
                msg_postfix = " Source not deleted." 
            print(_FA + f" ffmpeg concat to '{__ext}' failed." + msg_postfix)

            return False

        return True


    if args.tracks_overlay :

        to_res = concatvideos_filter(args.tracks_overlay, f'{OUTPUT_NAME}', __ext, args.yes_please, args.clear) #False, args.clear)
        if to_res == True:
            print(_OK + f" combining to '{__ext}' successfuly finished. Output: '{DATA_DIR}/{OUTPUT_NAME}{__ext}'")

        else:
            msg_postfix = ""
            if args.clear :
                msg_postfix = " Source not deleted."
            print(_FA + f" combining to '{__ext}' failed." + msg_postfix)

            return False

        return True


    if args.convert :
               
        conv_inp_arg_str = ''.join(args.convert)

        # check if specified output extension is
        # not simillar with source's file extension
        if conv_inp_arg_str.strip().endswith(__ext) :
            print(f'Source\'s file extension is simillar with provided. Abort..')

            return False
        
        if args.reencode :
            print(LONG_OP)

        convert_res = ffmpeg_convert(''.join(args.convert), f'{OUTPUT_NAME}', __ext, args.yes_please, args.clear, args.reencode) #False,args.clear, args.reencode)
        if convert_res == True:
            print(_OK + f" converting successfuly finished. Output: '{DATA_DIR}/{OUTPUT_NAME}{__ext}'")

        else:
            msg_postfix = ""
            if args.clear :
                msg_postfix = " Source not deleted."
            print(_FA + f" converting failed." + msg_postfix)

            return False

        return True



    if args.url or args.rutube:
        tprint('[Download]')
        
        URL= ''

        if args.rutube :
            tprint("[Rutube]")

            if not HAVE_RTB_MODULE :
                print(f"{_WA} RTB module is missing. Exiting..")
                return False

            tmp_name = ""
            URL, tmp_name = get_rtb_link(args.rutube[0], args.rutube[1])
            
            if tmp_name != "" and is_output_name_dflt :
                OUTPUT_NAME = tmp_name
        else :
            URL = f"{''.join(args.url)}"

        
        if not download_chunks(f'{URL}', RAW_DATA_DIR, args.allow_failed_snippets,args.download_missing_only, args.continue_interrupted_download): # if download failed
            print(">> Abort download..")
            if args.clear:
                remove_files(RAW_DATA_DIR,__raw_ext)   

            return False

    if args.merge or (not args.merge and not args.download):
        tprint('[Merging]')

        return merge2output_format(f'{OUTPUT_NAME}',  __ext, RAW_DATA_DIR, args.clear, args.yes_please)


    return True
#defend


if __name__ == "__main__":

    # start screen 'stars'
    print(f"{'*'*os.get_terminal_size().columns}")

    print(_D + f" Main thread PID: {str(get_pid())}")

    args = get_args()

    if args.version :
        print(f'{_NAME + " " + curVer}')
        sys.exit(0)

    if main_logic(args) == True :
        print(_OK + " Program finished successfuly.")
    else :
        print(_FA + " Something goes wrong..")

    print('Done.')



