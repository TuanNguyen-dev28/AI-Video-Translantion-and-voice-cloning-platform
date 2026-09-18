"""
Timing utility functions for audio sync.
"""
from typing import List, Dict


def milliseconds_to_srt_time(ms: int) -> str:
    """Convert milliseconds to SRT time format."""
    seconds = ms / 1000
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(ms % 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def seconds_to_srt_time(seconds: float) -> str:
    """Convert seconds to SRT time format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def format_duration(seconds: float) -> str:
    """Format duration as human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"


def calculate_speed_ratio(original_duration: float, target_duration: float) -> float:
    """Calculate speed ratio to fit target duration."""
    if target_duration <= 0:
        return 1.0
    return original_duration / target_duration


def fit_segments_to_timeline(
    segments: List[Dict],
    segment_durations: List[float],
    tolerance: float = 0.1,
) -> List[Dict]:
    """
    Fit segments to original timeline, adjusting for timing differences.
    
    Args:
        segments: Original segment data
        segment_durations: Actual TTS segment durations
        tolerance: Acceptable time difference
        
    Returns:
        Adjusted segments with padding info
    """
    adjusted = []
    
    for seg, tts_dur in zip(segments, segment_durations):
        orig_start = seg.get("start", 0)
        orig_end = seg.get("end", 0)
        orig_dur = orig_end - orig_start
        
        diff = tts_dur - orig_dur
        
        adjusted_seg = seg.copy()
        adjusted_seg["tts_duration"] = tts_dur
        adjusted_seg["original_duration"] = orig_dur
        adjusted_seg["needs_padding"] = diff > tolerance
        adjusted_seg["padding_needed"] = max(0, diff)
        
        adjusted.append(adjusted_seg)
    
    return adjusted
