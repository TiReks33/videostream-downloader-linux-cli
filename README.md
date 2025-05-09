# videostream-downloader-linux-cli
## Description
Downloads input chunklist(.m3u8) of transport stream video by its URL and converts raw fragments to .mp4 (or other container format) video-file (by ffmpeg). Testing on Linux Debian OS 11.6 && FreeBSD 13.2.
## Depends
wget, ffmpeg, Python interpreter (testing on Python 3.9.2)
## Usage
Copy-paste your transport video's chunklist URL adress and put it as '--url'('-u') argument. This can be done by next method:  

[Instruction](videostream-downloader-instr.gif)  

You can only download raw materials for future converting by putting '-d'('--download') flag (raw .ts fragments can be found in '$HOME/\_\_VIDEOSTREAM_DOWNLOADER_OUTPUT\_\_/raw/' folder by default). And, accordingly, if chunks already presents in 'raw/' folder, you can merge it without re-download by '-m'('--merge') flag.  
If network is unstable, or videosnippets presented in chunklist is corrupted etc., you can set '--allow-failed-snippets'('-a') flag to avoid terminating of snippets download after first fail.  
You may concat several videofiles files in 1 with '--concat'('-cc') flag with providing a videofiles paths you want to concat (this may very usefull if whole videostream is divided into several separated chunklists, and with this option you may 'recover' original video from separated parts).  
Default paths can be overrided by '--outputDir', '--rawDir', '--tempDir' flags.
If previous download of chunks from list failed, you can set '--continue-interrupted-download' or 'download-missing-only' flag.   
### CLI args  
```
  -h, --help            show this help message and exit  
  -u URL, --url URL     pass URL of chunklist here  
  -m, --merge           flag to only merge existing(in 'raw' subdir) .ts chunks to .mp4 file without downloading  
  -o OUTPUT [OUTPUT ...], --output OUTPUT [OUTPUT ...]  
                        output .mp4 file name (white-spaces and not-latin characters (4ex., cyrillic etc.) supported)  
  -d, --download        flag to only download chunklist without merging to video-file (will be ignored with '--merge'
                        or '--concat' flags)  
  -a, --allow-failed-snippets  
                        this flag skips script terminating after 'wget' failed to download a (corrupted) videosnippet  
  -cc CONCAT [CONCAT ...], --concat CONCAT [CONCAT ...]  
                        provide .mp4 file name/s (part/s) path/s to input for concat it to 1 video; this flag is usefull
                        in situations when you have several already converted(merged) .mp4
                        videos (4ex., several parts of 1 whole videostream, downloaded and merged via separate
                        chunklists). Note: video parts will be provided to concat in the sequence of arguments.  
  -cl, --clear          clear chunks folder after converting successfully finished (ignoring if '--download' flag is
                        used)  
  --outputDir OUTPUTDIR  
                        replace default output .mp4 file dir by this path  
  --rawDir RAWDIR       replace default raw chunks dir by this path  
  --tempDir TEMPDIR     replace default temporary files dir by this path  

Download raw chunks options:  
  This options group included some [exclusive] parameters for "--download" stage.  

  --download-missing-only  
                        Existing raw .ts files chunks in '--rawDir' (if any) will be preserved without rewriting. Note:
                        this method [guarantees] that it's only download missing chunks from list, BUT it's nothing to
                        do with [partially downloaded] files. Use it if you don't care about file
                        integrity/completeness, or you sure of this in advance.  
  --continue-interrupted-download  
                        Partially downloaded or corrupted raw .ts chunks files of [previous failed/interrupted download]
                        will be re-downloaded from chunks-list (along with missing ones), with replacement of existing.
                        Note: use this method [ONLY] if previous download of chunk-list's raw files has been interrupted
                        or failed at some progress stage; otherwise correct output not guaranteed.  

Merge options:  
  This options group is for "--merge" stage, and also for '--concat' option.  

  --ts                  set this parameter for '--merge' stage (or when you use '--concat' option), if you want to keep
                        output file in '.ts' format without converting to '.mp4'.  
  --mkv                 set this parameter for '--merge' stage (or when you use '--concat' option), if you want to use
                        '.mkv' container format for your output formatting instead of '.mp4'.  
  --mov                 set this parameter for '--merge' stage (or when you use '--concat' option), if you want to use
                        '.mov' container format for your output formatting instead of '.mp4'.  
  --avi                 set this parameter for '--merge' stage (or when you use '--concat' option), if you want to use
                        '.avi' container format for your output formatting instead of '.mp4'.
  
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
foo@bar:~$ python3 videostream-downloader-linux-cli.py -cc /path/to/video1.mp4 '/path/to/fine video2.mp4' -o
2in1video.mp4
```
```console
foo@bar:~$ python3 videostream-downloader-linux-cli.py --rawDir /path/to/raw/ts/chunks/ --outputDir /output/path/  
--tempDir /path/to/temporary/files/ -o nameOfOutputFile -cl -u https://*chunklist_link*.m3u8 --download-missing-only
```
```console
foo@bar:~$ python3 videostream-downloader-linux-cli.py -m -o outputName --mkv --outputDir /some/path/to/output/ --clear
```



