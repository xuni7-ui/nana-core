"""Original-source-gated PUBLIC audio measurements; no observation authority."""
from dataclasses import dataclass,field

from nana_core.nanalink.video_handoff import with_current_public_video
from tools.nana_next_experience.experiments.video_audio_probe import measure
from tools.nana_next_experience.experiments.video_cached_snapshot import public_snapshot


@dataclass(frozen=True,repr=False)
class GuardedAudioWindow:
    source_ref: str
    source_sha256: str
    acoustic: dict = field(repr=False)
    cache_bytes_hashed: int = 0
    state: str = 'MEASUREMENT_NOT_INGESTED'
    source_lifetime: str = 'RECHECK_REQUIRED_AT_USE'
    timeline_alignment: str = 'CALLER_MUST_VERIFY'


def guarded_audio_window(app,cache,source_memory_id,*,scope,start_seconds,end_seconds):
    """Measure a current PUBLIC video's hashed bytes with the original Store gate.

    No platform/byte attestation, subtitle alignment, speech or permission claim
    is created. The original source and authorization must be rechecked when
    using the returned in-memory candidate. Normal cleanup is not crash cleanup.
    """
    def operation(handle):
        with public_snapshot(cache,handle,privacy='PUBLIC') as path:
            acoustic=measure(path,start_seconds=start_seconds,end_seconds=end_seconds)
        return GuardedAudioWindow(source_ref=source_memory_id,source_sha256=handle.sha256,
                                  acoustic=acoustic,cache_bytes_hashed=handle.size)
    return with_current_public_video(app,cache,source_memory_id,scope=scope,operation=operation)
