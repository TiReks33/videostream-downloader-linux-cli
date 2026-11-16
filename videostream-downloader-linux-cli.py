#!/bin/python3

_NAME='videostream-downloader-linux-cli'
curVer = "[v0.9]"

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
from fake_headers import Headers


G_http_headers_dict = ''
G_wget_headers_str = ''


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

INIT_F_MARK = '#'


def get_pid() -> int :
    return threading.get_native_id()


MAIN_THREAD_PID = get_pid()


def tprint(text : str) -> None :
    prefix = "[MAIN_THREAD] " if get_pid() == MAIN_THREAD_PID else f"[ThreadPID:{get_pid()}] "
    print(prefix + text)

# major formats file extensions
class ext_enum(str, Enum):
    #video-specific formats extensions
    ts    = 'ts'  # MPEG2 transport stream (.m3u8) 
    m4s   = 'm4s' # Apple HLS (.m3u8)
    mp4   = 'mp4'
    mkv   = 'mkv'
    avi   = 'avi'
    mov   = 'mov'
    #audio-specific
    mp3   = 'mp3'
    aac   = 'aac'
    flac  = 'flac'
    wav   = 'wav'
    m4a   = 'm4a'

    def __str__(self) -> str:
        return str.__str__(self)


# size in bytes, 'ext_' expects '.txt' extension format, not 'txt'
def get_dir_files_size_amount(path='.',recurs: bool=True, ext_: str = None):

    if ext_ != None :
        ext_ = ext_.strip()
        if ext_ != '' and not ext_.startswith('.') :
            ext_ = f'.{ext_}'
    
    files_amount = 0
            
    def scan_dir(path_: str) :
        nonlocal files_amount
        total = 0
        with os.scandir(path_) as it:
            for entry in it:
                if entry.is_file():
                    if ext_ != None and pathlib.Path(entry).suffix != ext_ :
                        continue
                    
                    total += entry.stat().st_size
                    files_amount += 1
                elif recurs and entry.is_dir():   
                    total += scan_dir(entry.path)#get_dir_files_size_amount(entry.path, recurs, ext_)
        return total
    #defend
    
    total_size = scan_dir(path)
    
    print("$get_dir_files_size_amount::files_amount==", files_amount)
    
    return total_size


def yes_or_no(question) -> bool :

    reply = str(input(question + " ([Y]es/[N]o): ")).strip()

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

    reply = str(input(question + " ([Y]es/[N]o/[A]bort): ")).strip()

    if reply == 'y' or reply == 'Y' or reply == 'yes' or reply == 'Yes' or reply == 'YES' :
        return Answer.Yes
    elif reply == 'n' or reply == 'N' or reply == 'no' or reply == 'No' or reply == 'NO' :
        return Answer.No
    elif reply == 'a' or reply == 'A' or reply == 'abort' or reply == 'Abort' or reply == 'ABORT' :
        return Answer.Abort
    else:
        return yes_no_abort("Please, enter 'yes'(y), 'no'(n) or 'abort'(a)")


def prompt(question):
    return str(input(question + ' ')).strip()


def getFilesInDir(path: str, ext_ = None, include_path: bool = False) -> list :

    result = []
    joined_path = ''
    el2add = ''

    for el in os.listdir(path) :
        joined_path = os.path.join(path, el)
        if os.path.isfile(joined_path) :
            if ext_ and not el.endswith(ext_) :
                continue
            if include_path :
                el2add = f'{path}/{el}'
            else :
                el2add = el
                
            result.append(el2add)

    return result
#defend


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


### Custom sort comparator for marked HLS init files (#EXT-X-MAP:URI=) (for 'merge' stage) --> 
def natural_key(text):
    # Splits "1.m4s" into [1, ".m4s"] for numeric comparison
    return [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', text)]

def custom_sort(filename):
    fname, ext = os.path.splitext(filename)
    
    if fname.endswith(INIT_F_MARK) :
        is_marked = True
        base_name = fname[:-1] + ext
    else :
        is_marked = False
        base_name = filename
    
    # Priority 0 (marked) comes before Priority 1 (unmarked)
    priority = 0 if is_marked else 1
    
    return (natural_key(base_name), priority)
### <--


def uniquify_path(path):
    filename, extension = os.path.splitext(path)
    counter = 1

    while os.path.exists(path):
        path = filename + " (" + str(counter) + ")" + extension
        counter += 1

    return path


def download_chunks(chunklist_url: str, RAW_DATA_DIR: str, skip_corrupted_snippets=False, keep_existing_chunks: bool=False, continue_previous: bool=False) -> bool :

    SRAW_DATA_DIR=shellSpaceEscape(RAW_DATA_DIR) # local (arg) instead of global ..
    SDOWNLOAD_ERRORS_LOG_F=shellSpaceEscape(DOWNLOAD_ERRORS_LOG_F)    

    if keep_existing_chunks :
        print(f'{_D} \'--download-missing-only\' flag activated.')
    elif continue_previous :
        print(f'{_D} \'--continue-interrupted-download\' flag activated.')
 
    tprint(">> Processing..")

    tprint(">> Downloading chunklist..")

    chunklist_f_name = "hls_chunklist" # chunklist_url.split("/")[-1]

    chunklist_f_name = remove_fat_ntfs_illegal_chars(chunklist_f_name)

    chunklist_path = os.path.join(RAW_DATA_DIR, chunklist_f_name)

    downl_chunklist = f"wget '{chunklist_url}' -O {SRAW_DATA_DIR}/{chunklist_f_name} {G_wget_headers_str}"

    print("wget chunklist command:", downl_chunklist)

    wget_call_exit_code = os.system(downl_chunklist)

    if wget_call_exit_code != 0:
        print(_FA + " Wget download of chunklist failed (is provided URL correct?).")
        return False

    with open(chunklist_path, "r") as f:
        # load downloaded chunklist to memory
        chunklist = f.read()

    remove_file(chunklist_path)

    # Chunks download and processing..

    # 0) parse only files from chunklist
    tprint(">> Grouping chunks..")
    base_url = "/".join(chunklist_url.split("/")[:-1])

    file_pattern = re.compile(f"[^\n].*\\{__raw_ext}")
    raw_file_list = list(sorted(re.findall(file_pattern, chunklist)))

    #print("\n\n$raw_file_list==", raw_file_list)

    url_outpath_dict = dict()
    clear_uri = ''
    output_el = ''

    for ind, substr in enumerate(raw_file_list) :
        #
        # 3.4.13.  EXT-X-MAP (tag, introduced in draft-09 of the HLS spec)
        #
        # The EXT-X-MAP tag specifies how to obtain the Transport Stream PAT/
        # PMT for the applicable media segment.  It applies to every media
        # segment that appears after it in the Playlist until the next EXT-X-
        # DISCONTINUITY tag, or until the end of the playlist.
        #
        start_xmap = substr.startswith("#EXT-X-MAP")

        # remove_metadata_init_file_tag
        if start_xmap :

            uri = "URI=\""

            uri_index = substr.find(uri)

            clear_uri = substr[uri_index + len(uri):]

            #print("\n\n$clear_uri==", clear_uri)

            if clear_uri in url_outpath_dict :
                continue

            clear_filename = pathlib.Path(clear_uri).stem

            #print("$clear_filename==", clear_filename)

            marked_init_el = f'{clear_filename}{INIT_F_MARK}{__raw_ext}'

            #print("$marked_init_el==", marked_init_el)

            output_el = marked_init_el

        else:

            if substr in url_outpath_dict :
                continue
            
            clear_uri = substr

            output_el = clear_uri.split("/")[-1] #f'{RAW_DATA_DIR}/{clear_uri.split("/")[-1]}'


        new_content = ""

        output_fname_append = f' -O "{RAW_DATA_DIR}/{output_el}"'

        if clear_uri.startswith("http") :
            new_content = clear_uri + output_fname_append
        else :
            new_content = f"{base_url}/{clear_uri}" + output_fname_append

        url_outpath_dict[clear_uri] = [output_el, new_content]

    #endfor

    #print("\n\nurl_outpath_dict==")

    #for key, value in url_outpath_dict.items():
    #    print("URI:", key, " ", "COMMAND:", value)
    #    print("")

    file_count_before=len(url_outpath_dict)


    if keep_existing_chunks :

        only_unique_list = []

        existing_files_in_raw_dir = list(getFilesInDir(RAW_DATA_DIR))

        for filename in existing_files_in_raw_dir :
            for key, value in url_outpath_dict.items() :
                if value[0] == filename :
                    del url_outpath_dict[key]
                    break


    #print("\n\n url_outpath_dict==")

    #for key, value in url_outpath_dict.items():
    #    print("URI==", key, " ", "COMMAND==", value)
    #    print("")

    file_count=len(url_outpath_dict)

    print("\n\n$file_count_before:", file_count_before, "::", " file_count after:", file_count)

    if keep_existing_chunks and not file_count :
        print(f'Nothing to download.. All chunks already in {RAW_DATA_DIR}')
        return True

    url_outpath_dict_values_list = [value[1] for value in url_outpath_dict.values()]

    url_chunks = []
    for i in range(10):
        start_i = round(i * file_count / 10)
        end_i = min(round((i + 1) * file_count / 10), file_count)
        url_chunks.append(url_outpath_dict_values_list[start_i:end_i])
    assert sum([len(c) for c in url_chunks]) == file_count

    #print("\n\n$url_chunks:", url_chunks)


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
                
                
                wget_call_command = f"wget {additional_flags4downl} --quiet " + url_portion + f" 2>>{SDOWNLOAD_ERRORS_LOG_F} {G_wget_headers_str}"
                
                #print("thread::wget_call_command:", wget_call_command)

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
        results = []

        for i, el in enumerate (urls_string_list) :

            threads[i] = Thread(target = single_url_proceed, args=(el, results, silent))
            threads[i].start()
        
        # running threads processing join
        for thr_el in threads :
            thr_el.join()

        ## threads execution results return
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

            tprint(f"{_D} snippets portion list is empty, nothing to proceed..")


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

    stitle=shellSpaceEscape(title)
    SDATA_DIR=shellSpaceEscape(DATA_DIR)
    SRAW_DATA_DIR=shellSpaceEscape(RAW_DATA_DIR) # local (arg) instead of global..
    STEMP_DIR=shellSpaceEscape(TEMP_DIR)

    MERGED_F_FULL_PATH = os.path.join(DATA_DIR, f'{title}{__ext}')
    #SMERGED_F_FULL_PATH = shellSpaceEscape(MERGED_F_FULL_PATH)

    # 0) check raw dir exists
    if not os.path.exists(f"{RAW_DATA_DIR}") :
        print(f'{_FA} "raw" data dir with chunks files not found in chosen destination. Exiting..')

        return False
    else :
        files_in_raw_dir = os.listdir(RAW_DATA_DIR)
        
        # 1) check raw dir is not empty
        if len(files_in_raw_dir) == 0 :
            print(f'{_FA} "raw" data dir is empty. Nothing to merge. Exiting..')
            return False
        else :
            # 2) if not empty, check if files with given 'raw' extension exists in it
            raw_ext_files_count = sum(1 for file in files_in_raw_dir if file.endswith(__raw_ext))

            print("raw_ext_files_count:", raw_ext_files_count)

            if not raw_ext_files_count:
                print(f'{_FA} "raw" data dir include no files with given extension (\'{__raw_ext}\') for merging. Exiting..')
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
                #SMERGED_F_FULL_PATH=shellSpaceEscape(MERGED_F_FULL_PATH)
            elif answ is Answer.Abort :
                print("Aborting..")
                return False
            else :
                overwrite_out_file=True
 

    RAW_SIZE=int(get_dir_files_size_amount(RAW_DATA_DIR, False, __raw_ext)) # <-------------------------------------
    
    print("$RAW_SIZE==", RAW_SIZE)

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

            mes=f'{_FA} {_NOSPACE} Free space in temp files folder ({TEMP_DIR}, ' \
                f'logical device:{TEMP_VOL}): {AVAILABLE_IN_TEMP}. Approximately required space at least: {TEMP_REQ}.' #{OP_REQ_SPACE}.'
                #f'logical device:{TEMP_VOL}): {AVAILABLE_DISK_SPACE}. Approximately required space at least: {TEMP_REQ}.' #{OP_REQ_SPACE}.'

            print(mes)

            return False

        if overwrite_out_file : 
            OP_REQ_SPACE  = OP_REQ_SPACE - getFileSize(MERGED_F_FULL_PATH) 

        if AVAILABLE_DISK_SPACE < OP_REQ_SPACE :

            mes=f'{_FA} {_NOSPACE} Free space ({DATA_DIR}, logical device:{DATA_VOL}): ' \
                f'{AVAILABLE_DISK_SPACE}. Approximately required space at least: {OP_REQ_SPACE}.'

            print(mes)

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

            mes=f'{_FA} {_NOSPACE} Free space ({DATA_DIR}, logical device:{DATA_VOL}): ' \
                f'{AVAILABLE_DISK_SPACE}. Approximately required space at least: {OP_REQ_SPACE}.'

            print(mes)

            return False
  

    tprint(">> Converting in progress (merging stage)..")
    
    # custom sort for determine beginning of new initialization section (by special init mark postfix)
    partLis_ = sorted(getFilesInDir(RAW_DATA_DIR, __raw_ext, True), key=custom_sort)
  
    #print("\n\n$partLis_==", partLis_)
    
    it = 0
    init_sections_sublists = [[]]
    
    for el in partLis_ :
        cl_el = os.path.splitext(el)[0]

        if init_sections_sublists[it] and cl_el.endswith(INIT_F_MARK) :
            it += 1
            init_sections_sublists.append([])

        init_sections_sublists[it].append(el)
    
    #print("\n\n$init_sections_sublists==", init_sections_sublists)
    
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


    def init_sections_processing(partLis: list, SECTION_TMP: str, SECTION_OUTP: str) -> bool :
        
        # local OUTP_EXT, but '__raw_ext' is global
        OUTP_EXT = os.path.splitext(SECTION_OUTP)[1]
        print("$OUTP_EXT:", OUTP_EXT)
        
        exit_result = False

        cc_error=f'{_FA} there is error while merging chunks.'

        # simplification for raw output file format
        if OUTP_EXT == __raw_ext:

            # case if only 1 raw file gets merged
            if len(partLis) == 1 :
                
                print("OUTP_EXT == __raw_ext, only 1 raw file case")
                
                print(f"Nothing to merge -- there is only one {__raw_ext} file already in {RAW_DATA_DIR}.")

                src_raw_file = partLis[0]
                
                print(f"Copying source file to destination path ('{SECTION_OUTP}')...")
                
                try:
                    shutil.copy(src_raw_file, SECTION_OUTP)
                    if clear_raw:
                        remove_file(src_raw_file)
                    return True
                except PermissionError:
                    print(f"{_FA} file '{src_raw_file}' permission error (maybe it is open in another process?).")
                except FileNotFoundError:
                    print(f"{_FA} file '{src_raw_file}' does not exist.")
                except Exception as e:
                    print(f"An unexpected error occurred: {e}")

                return False

            else :

                print("OUTP_EXT == __raw_ext, more than 1 raw files case")

                if overwrite_out_file :
                    remove_file(SECTION_OUTP)

                exit_result = merge_to_one(partLis,SECTION_OUTP,clear_raw)
    
                if exit_result == False :
                    print(cc_error)

                
        else :

            # case if only 1 raw file gets merged
            if len(partLis) == 1 :
                
                print("OUTP_EXT != __raw_ext, only 1 raw file case")

                exit_result = concatmedia(partLis,SECTION_OUTP, OUTP_EXT, overwrite_out_file, clear_raw)

            else :

                print("OUTP_EXT != __raw_ext, more than 1 raw files case")

                exit_result = merge_to_one(partLis,SECTION_TMP,clear_raw)
                if exit_result == False :
                    print(cc_error)

                    return False

                exit_result=concatmedia([SECTION_TMP], SECTION_OUTP, OUTP_EXT, overwrite_out_file, True)

        if exit_result == True:
            print(_OK + f" Merging finished. Output: '{SECTION_OUTP}'")
            return True
        else:
            print(_FA + f" Merging failed.")
            return False
    
    #defend


    init_sections_amount = len(init_sections_sublists)

    print("\n\n$init_sections_amount:", init_sections_amount)

    # IF STANDARD PLAYLIST WITH 1 INIT SECTION ->
    if init_sections_amount == 1 :
        
        TMP_F_PATH = uniquify_path(os.path.join(TEMP_DIR, f'{title}_temp{__raw_ext}'))
        
        return init_sections_processing(init_sections_sublists[0], TMP_F_PATH, MERGED_F_FULL_PATH)

    
    # NEXT -- IF PLAYLIST HAVE MORE THAN 1 INIT SECTION (i.e., stream record with bad signal) ->

    init_sections_paths_list = []

    # handle possible cases with multiply init sections ('#EXT-X-MAP:URI=..' tags in HLS scheme) included in one single playlist
    for ind, init_section in enumerate(init_sections_sublists):

        init_section_title = f'{title}{INIT_F_MARK}{ind}'
    
        #print("\n\n$init_section_title:", init_section_title)
        
        tfName=f'{init_section_title}_temp{__raw_ext}'
        
        init_section_temp_path = uniquify_path(os.path.join(TEMP_DIR, tfName))
        
        #print("\n\n$init_section_temp_path:", init_section_temp_path)
        
        init_section_outpath = uniquify_path(os.path.join(DATA_DIR, f'{init_section_title}{__raw_ext}')) #{__ext}'))
        
        #print("\n\n$init_section_outpath:", init_section_outpath)
        
        init_sections_paths_list.append(init_section_outpath)
            
        # each section output format == raw format
        if init_sections_processing(init_section, init_section_temp_path, init_section_outpath) : # init_section_title, __raw_ext) : 
            print(f"{_OK} Initialization section no.{ind} ('{init_section_outpath}') processed successfully.") # ('{init_section_title}' -> '{__raw_ext}') processed successfully.")
        else :
            print(f"{_FA} Processing of initialization section no.{ind} ('{init_section_outpath}') failed.") # ('{init_section_title}' -> '{__raw_ext}') failed.")
            return False
        
    if overwrite_out_file :
        remove_file(MERGED_F_FULL_PATH)
    
    init_sections_merging_res = merge_to_one(init_sections_paths_list, MERGED_F_FULL_PATH, True)#False)#clear_raw)
    # init_sections_merging_res = concatmedia(init_sections_paths_list, MERGED_F_FULL_PATH, __ext, overwrite_out_file, True)#False)#clear_raw)
    
    if init_sections_merging_res == False :
        print(f"{_FA} error occurred while merging separate init sequences to single file..")
        return False
    
    print(f"{_OK} final merging to single file finished. Output: '{MERGED_F_FULL_PATH}'.") 
    return True



# this function usefull for overlaying audio onto video part (Concat Filter used)
#ex-'concatvideos_filter'
def concatmedia_overlay(files_list: list, OUTP: str, __ext: str, overwrite_existing: bool=False, delete_source_after: bool = False) -> bool :

    cc_prot_list = []

    for el in files_list :

        fullfpath_command=f'realpath {Quote(el)}' #// need double quotes escape

        get_videofrealpath=subprocess.run(fullfpath_command, capture_output=True, shell=True)
        videofrealpath=get_videofrealpath.stdout.decode('utf-8').strip()

        cc_prot_list.append(f'{Quote(videofrealpath)}')        

    cc_prot_list_str = ' -i '.join(cc_prot_list)

    command2exec=f"ffmpeg -loglevel error -i {cc_prot_list_str}"
    
    if __ext == ".mp3":
        command2exec += " -vn -c:a libmp3lame"
    elif __ext == ".flac":
        command2exec += " -vn -c:a flac"
    else:
        command2exec += " -c copy"
    
    command2exec += f' "{OUTP}"'

    if overwrite_existing :
        command2exec+=" -y"

    print("concatmedia_overlay::__ext:", __ext)
    print("concatmedia_overlay::command2exec:", command2exec)

    result=subprocess.run(command2exec, shell=True)
   
    if result.returncode == 0 :
        if delete_source_after :
            for source_file in files_list:
                 remove_file(source_file)
        return True
    return False

#defend


# Concat Demuxer (from file)
# ex-'concatvideos'
def concatmedia(files_list: list, OUTP: str, __ext: str, overwrite_existing: bool=False, delete_source_after: bool = False) ->bool :

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

    # concat "demuxer"
    command2exec=f"ffmpeg -loglevel error -f concat -safe 0 -i {Quote(videolist_tempfname)}"
    
    if __ext == ".mp3":
        command2exec += " -vn -c:a libmp3lame"
    elif __ext == ".flac":
        command2exec += " -vn -c:a flac"
    else:
        command2exec += " -c copy"
    
    command2exec += f' "{OUTP}"'
    
    if overwrite_existing :
        command2exec+=" -y"
    
    print("concatmedia::__ext:", __ext)
    print("concatmedia::command2exec:", command2exec)

    result=subprocess.run(command2exec, shell=True)
   
    remove_file(videolist_tempfname)    

    if result.returncode == 0 :
        if delete_source_after :
            for source_file in files_list:
                 remove_file(source_file)
        return True
    return False

#defend


# ex-'ffmpeg_convert'
def media_convert(inp_file_path: str, OUTP: str, __ext: str, overwrite_existing: bool = False, delete_source_after: bool = False, reencoding: bool = False) -> bool :

    command2exec = ""
    if not reencoding :
        command2exec=f"ffmpeg -loglevel error -i {Quote(inp_file_path)}"
        
        if __ext == ".mp3":
            command2exec += " -vn -c:a libmp3lame"
        elif __ext == ".flac":
            command2exec += " -vn -c:a flac"
        else:
            command2exec += " -c copy"
    
        command2exec += f' "{OUTP}"'
        
    else :
        command2exec=f"ffmpeg -loglevel error -i {Quote(inp_file_path)} {OUTP}"        
    
    if overwrite_existing :
        command2exec+=" -y"
        
    print("media_convert::__ext:", __ext)
    print("media_convert::command2exec:", command2exec)

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

    ol_format = get_curr_output_format(args)

    vars(args)[new_format] = True

    if ol_format in vars(args) :
        vars(args)[ol_format] = False

#defend


def check_file_is_video(filepath: str) -> bool :

    file2check = filepath

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
                    print(f"'{filepath}' -- this is video!!")
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

    if result.returncode == 0 :
        res = result.stdout.decode().strip()
        if len(res.split()) == 1 and res == "audio" :
            print(f"'{filepath}' -- this is audio!!")
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
            print(f"'{chunklist_url}' -- is a audio chunklist's URL!!")
            return True

    return False
#defend


def get_rtb_link(url__ : str, pref_qual__: str = None) :
    link=''
    name=''
    try :
        link, name = get_rtb_src(url__, pref_qual__, G_http_headers_dict)
    
        name = remove_fat_ntfs_illegal_chars(name, '_')

        print("get_rtb_link(..)::extracted link:", link)
        print("get_rtb_link(..)::extracted name:", name)
    except :
        print(f"{_FA} get_rtb_link(..)::module function 'get_rtb_src(..)' returns exception." \
            " You can set different HTTP headers and try again.")

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

    parser.add_argument('-o','--outputName', help='output file name (white-spaces and not-latin characters (4ex., cyrillic etc.) supported)',nargs='+',default=None)#['output_file'])
    parser.add_argument('-d','--download',help='flag to only download chunklist, without merging to output file afterwards (works only with \'--url\' flag, will be ignored otherwise)',action='store_true')

    download_params_group = parser.add_argument_group('Download raw chunks options','This options group included some [exclusive] parameters for "--download" stage.')
    download_raw_chunks_options_ex_group=download_params_group.add_mutually_exclusive_group(required=False)
    
    download_raw_chunks_options_ex_group.add_argument('--download-missing-only', help='Existing raw files chunks in \'--rawDir\' (if any) will be preserved without rewriting. [Note]: this method [guarantees] that it\'s only download missing chunks from list, BUT it\'s nothing to do with [partially downloaded] files. Use it if you don\'t care about file integrity/completeness, or you sure of this in advance.',action='store_true')
    
    download_raw_chunks_options_ex_group.add_argument('--continue-interrupted-download', help='Partially downloaded or corrupted raw chunks files of [previous failed/interrupted download] will be re-downloaded from chunks-list (along with missing ones), with replacement of existing. [Note]: use this method [ONLY] if previous download of chunk-list\'s raw files has been interrupted or failed at some progress stage; otherwise correct output not guaranteed.',action='store_true')


    http_headers_params_group = parser.add_argument_group('HTTP headers options group','This options group included some [exclusive] parameters for setting a HTTP requests headers at "--download" stage. If none of this options is presented, no additional headers will be added to requests.')
    http_headers_options_ex_group=http_headers_params_group.add_mutually_exclusive_group(required=False)
    
    #0
    http_headers_options_ex_group.add_argument('--header', help='Option sets custom HTTP header; expects single HTTP header string. To set multiple headers, this option can be used repeatedly for each header that must be included ("wget"-style)', action='append', nargs=1, type=str)
    
    #1
    http_headers_options_ex_group.add_argument('--headers', help='Option sets custom HTTP headers; expects one or more HTTP headers strings (space separated)', nargs='+', type=str)
    
    #2
    http_headers_options_ex_group.add_argument('--headers-string', help='Option sets custom HTTP headers; expects single string with one or more HTTP headers, newline (\'\\n\') separated', nargs=1,type=str)
    
    #3
    http_headers_options_ex_group.add_argument('--headers-file', help='Option sets custom HTTP headers; expects path to file, that contains one or more HTTP headers, newline (\'\\n\') separated', nargs=1,type=str)
    
    #4
    http_headers_options_ex_group.add_argument('--random-headers', help='Option generates (once per program instance) random HTTP headers', action='store_true')
    
    #5
    http_headers_options_ex_group.add_argument('--basic-headers', help='Option generates (once per program instance) only basic HTTP headers, such as \'User-Agent\' identifier', action='store_true')

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
        # if no format passed via arguments -- default is '.mp4'
        change_curr_output_format(args, ext_enum.mp4)

    curr_format = get_curr_output_format(args)

    return args
#defend


# throws
def init_global_http_headers(args: argparse.Namespace) :
    
    global G_http_headers_dict, G_wget_headers_str
    
    def http_headers_string2dict(headers_string_ : str, separator_ : str = '\n') -> dict :
        
        headers_splitted_list = [line for line in headers_string_.split(separator_) if line.strip()] #headers_string_.split(separator_)
        
        result_headers_dict = {}
        
        try:
            for line in headers_splitted_list :
                # separate the HTTP header's key from the value by
                # first occurrence of colon (':')
                line_splitted = line.split(":", maxsplit=1)
                key = line_splitted[0].strip()
                
                if key == "": #key.strip() == "":
                    raise ValueError("cannot parse 'args.headers_string'; HTTP header's key cannot be empty.")
                
                value = line_splitted[1].strip()
                result_headers_dict[key] = value
        except: 
            raise ValueError("cannot parse 'args.headers_string'; colon (':') separated string data expected.")
        
        return result_headers_dict
    #defend
    
    result_dict = {}
    
    #0
    if args.header :

        try:
            for item in args.header :
                item_splitted = item[0].split(":", maxsplit=1)
                key = item_splitted[0].strip()
                
                if key == "":
                    raise ValueError("cannot parse 'args.header'; HTTP header's key cannot be empty.")
                
                value = item_splitted[1].strip()
                
                result_dict[key] = value
        except: 
            raise ValueError("cannot parse 'args.header'; colon (':') separated string data expected.")

    #1
    elif args.headers :
        try:
            for item in args.headers :
                item_splitted = item.split(":", maxsplit=1)
                key = item_splitted[0].strip()
                
                if key == "":
                    raise ValueError("cannot parse 'args.headers'; HTTP header's key cannot be empty.")
                
                value = item_splitted[1].strip()
                
                result_dict[key] = value
                
        except: 
            raise ValueError("cannot parse 'args.headers'; colon (':') separated string data expected.")

    #2
    elif args.headers_string :
        
        result_dict = http_headers_string2dict(args.headers_string[0])

    #3
    elif args.headers_file :
        
        try:
            f = open(args.headers_file[0], 'r')
        except OSError:
            raise ValueError("cannot parse 'args.headers_file'; cannot open file for read.")

        with f:
            headers_str = f.read()
            
            result_dict = http_headers_string2dict(headers_str)
            
    #4
    elif args.random_headers :
        result_dict = Headers(os="lin", headers=True).generate()
        
        if result_dict.get('Accept-Encoding') != None :
            del result_dict['Accept-Encoding'] # 'fix' to 'random' headers for not to use special compressions for delivery content (default utf-8)
    
    #5
    elif args.basic_headers :
        result_dict = Headers(os="lin", headers=False).generate()


    G_http_headers_dict = result_dict
    
    for k,v in G_http_headers_dict.items():
        if v == "" :
            G_wget_headers_str += f'--header="{k}:" '
        else :
            G_wget_headers_str += f'--header="{k}: {v}" '
            
    print ("G_http_headers_dict:", G_http_headers_dict)
            
    print("G_wget_headers_str:", G_wget_headers_str.strip())
            
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

                    t_outp_name_str = f"{' '.join(args.outputName)}_{ind}"

                    #if not args.download :
                    temp_args.outputName = [t_outp_name_str]

                    output_names += [ os.path.join(DATA_DIR, f'{t_outp_name_str}{__raw_ext}') ]

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
    if args.outputName is None :
        OUTPUT_NAME = 'output_file'
        is_output_name_dflt=True
    else:
        OUTPUT_NAME=f"{' '.join(args.outputName)}" # output file name


    #concat several videofiles to 1 
    if args.concat:
        print('[Concat existing videos]')

        cc_args = '::'.join(args.concat)#.strip('"')
        
        print(args.concat)
        print(f"{_D} cc_args::" + cc_args + ';')
        
        concat_outpath = os.path.join(DATA_DIR, f'{OUTPUT_NAME}{__ext}')
        
        ccres = concatmedia(args.concat, concat_outpath, __ext, args.yes_please, args.clear)

        if ccres == True:
            print(_OK + f" ffmpeg concat to '{__ext}' successfuly finished. Output: '{concat_outpath}'")

        else:
            msg_postfix = ""
            if args.clear :
                msg_postfix = " Source not deleted." 
            print(_FA + f" ffmpeg concat to '{__ext}' failed." + msg_postfix)

            return False

        return True


    if args.tracks_overlay :

        to_outpath = os.path.join(DATA_DIR, f'{OUTPUT_NAME}{__ext}')

        to_res = concatmedia_overlay(args.tracks_overlay, to_outpath, __ext, args.yes_please, args.clear)

        if to_res == True:
            print(_OK + f" combining to '{__ext}' successfuly finished. Output: '{to_outpath}'")

        else:
            msg_postfix = ""
            if args.clear :
                msg_postfix = " Source not deleted."
            print(_FA + f" combining to '{__ext}' failed." + msg_postfix)

            return False

        return True


    if args.convert :
               
        conv_inp_arg_str = ''.join(args.convert)
        
        if args.reencode :
            print(LONG_OP)

        conv_outpath = os.path.join(DATA_DIR, f'{OUTPUT_NAME}{__ext}')

        convert_res = media_convert(''.join(args.convert), conv_outpath, __ext, args.yes_please, args.clear, args.reencode)

        if convert_res == True:
            print(_OK + f" converting successfuly finished. Output: '{conv_outpath}'")

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
            
            if URL == "" :
                return False

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
    print(f"{'*'*shutil.get_terminal_size(fallback=(80,24)).columns}")

    args = get_args()

    if args.version :
        print(f'{_NAME + " " + curVer}')
        sys.exit(0)

    if not args.download :
        if os.system('command -v ffmpeg > nil') != 0:
            print(f"{_FA} check ffmpeg installation.")
            sys.exit(1)

    print(_D + f" Main thread PID: {str(get_pid())}")

    init_global_http_headers(args)

    if main_logic(args) == True :
        print(_OK + " Program finished successfuly.")
    else :
        print(_FA + " Something goes wrong..")

    print('Done.')


