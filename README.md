# ::[videostream-downloader-linux-cli[v0.89]]::
## Description
Downloads input chunklist(.m3u8) of media transport stream by its URL and converts raw fragments to .mp4/.mp3 or other container format of video/audio files (by ffmpeg). Testing on Linux Debian OS 11.6 && FreeBSD 13.2.
## Depends
wget, ffmpeg, Python interpreter (testing on Python 3.9.2)
  
## Usage
Copy-paste your transport media's chunklist URL adress and put it as '--url'('-u') argument. This can be done by next method:  

[Instruction](videostream-downloader-instr.gif)  
  
---
**Please note before use this software**:
> ***[This software is for testing purposes only; if you are not developer of corresponding platform (from which the multimedia source file is supposed to be downloaded), and/or you doesn't have legal permissions to direct access/download multimedia sources files from platform servers, you should remove all file/s that have been previously downloaded via this programm from your device, if any (unless otherwise permitted by your country local laws and platform rules). Be carefull and law abiding citizen!]***
---
  
You can only download raw materials for future converting by putting '-d'('--download') flag (raw '.ts'/'.m4s' fragments can be found in  
> '$HOME/\_\_VIDEOSTREAM_DOWNLOADER_OUTPUT\_\_/raw/'
  
folder by default). And, accordingly, if chunks already presents in 'raw/' folder, you can merge it without re-download by '-m'('--merge') flag.  
If network is unstable, or videosnippets presented in chunklist is corrupted etc., you can set '--allow-failed-snippets'('-a') flag to avoid terminating of snippets download after first fail.  
You may concat several videofiles files in 1 with '--concat'('-cc') flag with providing a videofiles paths you want to concat (this may very usefull if whole videostream is divided into several separated chunklists, and with this option you may 'recover' original video from separated parts).  
Default paths can be overrided by '--outputDir', '--rawDir', '--tempDir' flags.
If previous download of chunks from list failed, you can set '--continue-interrupted-download' or '--download-missing-only' flag.  
For more options see 'CLI args'.
  
### CLI args  
```
  -h, --help            show this help message and exit  
  -u URL, --url URL     pass URL of chunklist here  
  -rtb RUTUBE RUTUBE,   --rutube RUTUBE RUTUBE
                        resolve URL of resource. Takes 2 parameters: 1) resource url (to resolve it to .m3u8 link), 2) preffered video quality ('480p','720p', etc.).  
  -m, --merge           flag to only merge existing(in 'raw' subdir) .ts chunks to .mp4 file without downloading  
  -o OUTPUT [OUTPUT ...], --output OUTPUT [OUTPUT ...]  
                        output .mp4 file name (white-spaces and not-latin characters (4ex., cyrillic etc.) supported)  
  -d, --download        flag to only download chunklist without merging to video-file (will be ignored with '--merge'
                        or '--concat' flags)  
  -a, --allow-failed-snippets  
                        this flag skips script terminating after 'wget' failed to download a (corrupted) videosnippet  
  --customRaw CUSTOMRAW
                        custom format extension for raw chunks instead of '.ts' (4ex., '.aac' audio stream parts).  
  -cc CONCAT [CONCAT ...], --concat CONCAT [CONCAT ...]  
                        provide .mp4 file name/s (part/s) path/s to input for concat it to 1 video; this flag is usefull
                        in situations when you have several already converted(merged) .mp4
                        videos (4ex., several parts of 1 whole videostream, downloaded and merged via separate
                        chunklists). Note: video parts will be provided to concat in the sequence of arguments.  
  
  -t TRACKS_OVERLAY TRACKS_OVERLAY, --tracks-overlay TRACKS_OVERLAY TRACKS_OVERLAY
                        provide file/s (part/s) path/s of track/s for overlaying them 1 on 1; this flag can be usefull in situations when you have 2 separate parts of 1 media entity (4ex., audio- and video- separated parts of '.m4s' video), and you need to unite them to 1 monolitic file (with one-on-one overlay).  
  
  --convert CONVERT     provide input file to convert to specific output format via ffmpeg (format can be specified by '--{format}' flag (see '--help' for all available formats list).  
  
  -cl, --clear          clear chunks folder after converting successfully finished (ignoring if '--download' flag is used)  
  
  --outputDir OUTPUTDIR  
                        replace default output .mp4 file dir by this path  
  --rawDir RAWDIR       replace default raw chunks dir by this path  
  --tempDir TEMPDIR     replace default temporary files dir by this path
  
  -y, --yes-please      "Technical" flag. This flag is for skipping (automaticly confirming) question dialogs (4ex., about overwriting directory).[WARNING]: if this flag is set, You will lose the possibility to rename a file if it already exists; it will be forcibly replaced.  
    
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
Convert additional flags group:  
  This group included some flags for "--convert" parameter.
  
  --reencode            If this flag is set, output file's audio/video frames will be reencoded (quality of output video/audio may be differ than source). [Note]: this much longer operation then copying existing frames from input source; more rational use of this is only in case if execution of '--convert' without this flag gives output file of specified format not in satisfying state (4ex., video sequence of output is freezes/in low frame rate etc.).  
  
Output formats:  
  This options group is for '--merge' stage, and also for '--concat', '--tracks-overlay', '--convert' options; specify output data formatting (default is '.mp4').  
  
  --ts                  set this parameter if you want to use '.ts' format for your output data.  
  --m4s                 set this parameter if you want to use '.m4s' format for your output data.  
  --mkv                 set this parameter if you want to use '.mkv' format for your output data.  
  --mov                 set this parameter if you want to use '.mov' format for your output data.  
  --avi                 set this parameter if you want to use '.avi' format for your output data.  
  --mp4                 set this parameter if you want to use '.mp4' format for your output data.  
  --aac                 set this parameter if you want to use '.aac' format for your output data.  
  --mp3                 set this parameter if you want to use '.mp3' format for your output data.  
  --flac                set this parameter if you want to use '.flac' format for your output data.  
  --wav                 set this parameter if you want to use '.wav' format for your output data.  
  
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
```console
foo@bar:~$ python3 videostream-downloader-linux-cli.py -u https://example_url1/video.mp4/v1/index.m3u8 https://example_url1/video.mp4/a1/index.m3u8  --customRaw=m4s --output 123test -cl -y
```
```console
foo@bar:~$ python3 videostream-downloader-linux-cli.py --tracks-overlay ~/__VIDEOSTREAM_DOWNLOADER_OUTPUT__/123testA0.m4s ~/__VIDEOSTREAM_DOWNLOADER_OUTPUT__/123testA1.m4s --output 123TestA --mkv
```
```console
foo@bar:~$ python3 videostream-downloader-linux-cli.py --convert ~/__VIDEOSTREAM_DOWNLOADER_OUTPUT__/123testA.mp4 -o 123testA_reencoded --avi --reencode
```



