# videostream-downloader-linux-cli
## Description
Downloads input chunklist(.m3u8) of transport stream video by its URL and converts raw fragments to .mp4 video-file (by ffmpeg).
## Depends
ffmpeg, Python interpreter (testing on Python 3.9.2)
## Usage
Copy-paste your transport video's chunklist URL adress and put it as '--url'('-u') argument. This can be done by next method:  

[Instruction](videostream-downloader-instr.gif)  

You can only download raw materials for future converting by putting '-d'('--download') flag (raw .ts fragments can be found in '$HOME/\_\_VIDEOSTREAM_DOWNLOADER_OUTPUT\_\_/raw/' folder). And, accordingly, if chunks already presents in 'raw/' folder, you can merge it without re-download by '-m'('--merge') flag.  
If network is unstable, or videosnippets presented in chunklist is corrupted etc., you can set '--allow-failed-snippets'('-a') flag to avoid terminate after first fail.  
You may concat several .mp4 files in 1 with '--concat'('-cc') flag with providing a videofiles paths you want to concat (this may very usefull if whole videostream is divided into several separated chunklists, and with this option you may 'recover' original video from separated parts).   
### CLI args  
```
  -h, --help            show this help message and exit  
  -u URL, --url URL     pass URL of chunklist here  
  -m, --merge           flag to only merge existing(in 'raw' subdir) .ts  
                        chunks to .mp4 file without downloading  
  -o OUTPUT [OUTPUT ...], --output OUTPUT [OUTPUT ...]  
                        output .mp4 file name (white-spaces and not-latin  
                        characters (4ex., cyrillic etc.) supported)  
  -d, --download        flag to only download chunklist without merging to  
                        video-file (will be ignored with '--merge' or '--  
                        concat' flags)
  -a, --allow-failed-snippets  
                        this flag skips script terminating after 'wget' failed  
                        to download a (corrupted) videosnippet  
  -cc CONCAT [CONCAT ...], --concat CONCAT [CONCAT ...]  
                        this flag is usefull in situations when you have  
                        several already converted(merged) .mp4 videos (4ex.,  
                        several parts of 1 whole videostream, downloaded and  
                        merged via separate chunklists); provide .mp4 file  
                        names (parts) paths in input to concat it to 1 video.  
                        Note: video parts will be provided to concat in the  
                        sequence of arguments.  
  -cl, --clear          clear chunks folder after converting successfully  
                        finished (ignoring if '--download' flag is used)  
```
## Example usage
```console
foo@bar:~$ python3 videostream-downloader-linux-cli.py -u https://*chunklist_link*.m3u8 -o mine_video -cl
```
```console
foo@bar:~$ python3 videostream-downloader-linux-cli.py -u https://*chunklist_link*.m3u8 -d -a
```
```console
foo@bar:~$ python3 videostream-downloader-linux-cli.py --merge -o merged_video_from_early_downloaded_ts_fragments.mp4
```
```console
foo@bar:~$ python3 videostream-downloader-linux-cli.py -cc /path/to/video1.mp4 '/path/to/fine video2.mp4' -o 2in1video.mp4
```
