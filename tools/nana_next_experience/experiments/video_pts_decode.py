"""Local, bounded RGB decoding with actual FFmpeg output PTS, never a source authority."""
from dataclasses import dataclass, field
from decimal import Decimal
from fractions import Fraction
import json
import math
from pathlib import Path
import re
import subprocess


class FrameBoundExceeded(ValueError):
    """The window has more decoded frames than the explicit memory bound."""


@dataclass(frozen=True, repr=False)
class DecodedFrames:
    source_ref: str
    duration_seconds: float
    source_size: tuple[int,int]
    output_size: tuple[int,int]
    timestamps: tuple[float,...]
    rgb24: bytes = field(repr=False)
    pts_ticks: tuple[int,...] = ()
    time_base: tuple[int,int] = (0,1)
    timeline_origin: str = '0'
    video_start: str = '0'
    timestamp_basis: str = 'container_relative'
    duration_qualification: str = 'CONTAINER_DECLARED_UNVERIFIED'
    requested_window: tuple[float,float] | None = None
    window_state: str = 'FRAMES_DECODED_NOT_COVERAGE'
    declared_frames: int | None = None
    count_consistent: bool = False
    coordinate_space: str = 'decoded_scaled_pixels_no_rotation'
    source_attestation: str = 'CALLER_SUPPLIED'


def decode(source_ref, path, *, width=160, height=90, max_frames=1200, timeout=120,
           start_seconds=None, end_seconds=None):
    """Decode explicit local video in display order, preserving output PTS.

    Input identity and authorization are a caller responsibility. This helper
    does not persist frames, perform inference, or read a platform account.
    Preserve original integer PTS and the declared container timeline origin;
    derived seconds are container-relative, not a platform timestamp claim.
    """
    if (type(source_ref) is not str or not 1<=len(source_ref)<=128 or
            type(width) is not int or type(height) is not int or width<1 or height<1 or width*height>262144 or
            type(max_frames) is not int or not 1<=max_frames<=1200 or
            (start_seconds is None)!=(end_seconds is None)):
        raise ValueError('invalid decode bounds')
    path=Path(path).resolve(strict=True)
    if not path.is_file() or path.stat().st_size>256*1024*1024:raise ValueError('invalid local media')
    def run(command):
        try:return subprocess.run(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,check=True,timeout=timeout)
        except (OSError,subprocess.SubprocessError) as exc:raise ValueError('local video decode unavailable') from exc
    raw_info=run(['ffprobe','-v','error','-protocol_whitelist','file,pipe','-select_streams','v:0',
        '-show_entries','format=duration,start_time:stream=width,height,start_time,nb_frames',
        '-of','json',str(path)]).stdout
    if len(raw_info)>100000:raise ValueError('video metadata exceeds bound')
    try:
        info=json.loads(raw_info);stream=info['streams'][0];duration=float(info['format']['duration'])
        origin_text=str(info['format']['start_time']);video_start_text=str(stream['start_time'])
        if len(origin_text)>40 or len(video_start_text)>40:raise ValueError('oversized timing metadata')
        origin=Fraction(origin_text);video_start=Fraction(video_start_text)
        source_width=int(stream['width']);source_height=int(stream['height'])
    except (KeyError,IndexError,ValueError,TypeError) as exc:raise ValueError('unqualified video timing') from exc
    window=start_seconds is not None
    if window and (type(start_seconds) not in (int,float) or type(end_seconds) not in (int,float) or
                   not math.isfinite(start_seconds) or not math.isfinite(end_seconds) or
                   not 0<=start_seconds<end_seconds<=duration or end_seconds-start_seconds>600):
        raise ValueError('invalid decode window')
    if (not math.isfinite(duration) or not 0<duration<=(86400 if window else 600) or abs(origin)>2**53 or
            not 0<=video_start-origin<=Fraction(str(duration)) or source_width<1 or source_height<1):
        raise ValueError('unqualified video timing or dimensions')
    try:declared=int(stream['nb_frames'])
    except (KeyError,ValueError,TypeError):declared=None
    if declared is not None and declared<1:declared=None
    frame_size=width*height*3
    limit=min(max_frames,(64*1024*1024)//frame_size)
    # Read one extra frame to identify an exhausted bound, not silently truncate.
    command=['ffmpeg','-copyts','-hide_banner','-nostats','-loglevel','info','-protocol_whitelist','file,pipe']
    filters=f'scale={width}:{height}:flags=area,format=rgb24,showinfo'
    if window:
        # Fast seek is only an optimization; trim and post-check both use the
        # absolute source timeline, with end exclusive. No frame is invented.
        absolute_start=Decimal(origin_text)+Decimal(str(start_seconds))
        absolute_end=Decimal(origin_text)+Decimal(str(end_seconds))
        command+=['-ss',str(start_seconds),'-t',str(Decimal(str(end_seconds))-Decimal(str(start_seconds)))]
        filters=f'trim=start={absolute_start}:end={absolute_end},'+filters
    command+=['-noautorotate','-i',str(path),'-map','0:v:0','-vf',filters,
        '-fps_mode','passthrough','-an','-frames:v',str(limit+1),'-f','rawvideo','-pix_fmt','rgb24','-']
    result=run(command)
    if len(result.stdout)%frame_size:raise ValueError('partial decoded frame')
    count=len(result.stdout)//frame_size
    if count>limit:raise FrameBoundExceeded('decoded frame bound exceeded')
    if not window and count<1:raise ValueError('decoded frame bound exceeded')
    if len(result.stderr)>4*1024*1024:raise ValueError('decoder metadata exceeds bound')
    log=result.stderr.decode('utf-8',errors='replace')
    bases=re.findall(r'\[Parsed_showinfo_\d+\s+@[^\]]+\]\s+config in time_base:\s*(\d+)/(\d+)',log)
    if len(bases)!=1:raise ValueError('decoded frame time base unavailable')
    numerator,denominator=map(int,bases[0])
    if numerator<1 or denominator<1 or numerator>1000000000 or denominator>1000000000:
        raise ValueError('invalid decoder time base')
    pattern=re.compile(r'\[Parsed_showinfo_\d+\s+@[^\]]+\]\s+n:\s*(\d+)\s+pts:\s*(-?\d+)\s+pts_time:')
    rows=pattern.findall(log)
    if len(rows)!=count or any(int(row[0])!=i for i,row in enumerate(rows)):
        raise ValueError('decoded frame timestamps unavailable')
    ticks=tuple(int(row[1]) for row in rows)
    # Fraction avoids losing source tick precision while subtracting large origins.
    relative=tuple(Fraction(t*numerator,denominator)-origin for t in ticks)
    times=tuple(float(t) for t in relative)
    if window and any(not Fraction(str(start_seconds))<=t<Fraction(str(end_seconds)) for t in relative):
        raise ValueError('decoded frame outside requested window')
    if any(not math.isfinite(t) or not 0<=t<=duration for t in times) or any(a>=b for a,b in zip(times,times[1:])):
        raise ValueError('invalid decoded timestamp sequence')
    return DecodedFrames(source_ref=source_ref,duration_seconds=duration,source_size=(source_width,source_height),
        output_size=(width,height),timestamps=times,rgb24=result.stdout,pts_ticks=ticks,
        time_base=(numerator,denominator),timeline_origin=origin_text,video_start=video_start_text,
        requested_window=(start_seconds,end_seconds) if window else None,
        window_state='FRAMES_DECODED_NOT_COVERAGE' if count else 'NO_NEW_FRAME_DECODED_NOT_OBSERVED',
        declared_frames=declared,count_consistent=not window and declared is not None and count==declared)
