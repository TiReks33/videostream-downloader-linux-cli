# videostream-downloader-linux-cli
## Description
Downloads input chunklist(.m3u8) of transport stream video by its URL and converts raw fragments to .mp4 video-file (by ffmpeg).
## Depends
ffmpeg, Python interpreter (testing on Python 3.9.2)
## Usage
Copy-paste your transport video's chunklist URL adress and put it as -u(--url) argument. This can be done by next method:  

[Instruction](videostream-downloader-instr.gif)  

You can only download raw materials for future converting by putting '-d'('--download') flag (raw .ts fragments can be found in '*script_folder*/out/raw/' folder). And, accordingly, if chunks already presents in '/out/raw' folder, you can merge it without re-download by '-m'('--merge') flag.
### CLI args  
```
optional arguments:  
  -h, --help            show this help message and exit  
  -o OUTPUT [OUTPUT ...], --output OUTPUT [OUTPUT ...]  
                        output .mp4 file name (white-spaces and not-latin characters (4ex., cyrillic etc.) supported)  
  -d, --download        flag to only download chunklist without merging to video-file  
  -m, --merge           flag to only merge existing .ts data without downloading (URL parameter will be ignored)  
  -c, --clear           clear chunks folder after converting successfully finished (ignoring if --download flag is used)  
  
required arguments:  
  -u URL, --url URL     pass URL of chunklist here  
```
## Example
```console
foo@bar:~$ python3 videostream-downloader-linux-cli.py -u https://*chunklist_link*.m3u8 -o mine_video -c
```
