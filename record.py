#!/usr/bin/env python

import shlex
import argparse
import subprocess


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('rtsp_url')
    ap.add_argument('--segment-time', type=lambda x: str(int(x)), default='60')
    ap.add_argument('--output-prefix', default='ffmpeg')
    args = ap.parse_args()

    rtsp_url = shlex.quote(args.rtsp_url)
    segment_time = shlex.quote(args.segment_time)
    output_prefix = shlex.quote(args.output_prefix)
    _ffmpeg = f'''
        ffmpeg -i {rtsp_url}
        -loglevel error
        -rtsp_transport tcp
        -use_wallclock_as_timestamps 1
        -map 0 -vcodec copy -acodec copy
        -f segment -segment_time {segment_time} -segment_format matroska
        -segment_atclocktime 1
        -reset_timestamps 1 -strftime 1
        {output_prefix}_%Y-%m-%d_%H-%M-%S.mkv
    '''
    ffmpeg = shlex.split(_ffmpeg, comments=True)
    print(shlex.join(ffmpeg))
    subprocess.run(ffmpeg)


if __name__ == '__main__':
    main()
