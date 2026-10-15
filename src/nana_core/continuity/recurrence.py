"""Typed daily calendar, standard-library timezone/DST handling. No NLP or task."""
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
from typing import Literal
from pydantic import Field,model_validator
from ..contracts import DTO,CoreError
from ..storage import digest

EPOCH=datetime(1970,1,1,tzinfo=timezone.utc)

class RecurrenceSpec(DTO):
    kind: Literal['DAILY'] = 'DAILY'
    timezone: str = Field(pattern=r'^[A-Za-z_+-]+(?:/[A-Za-z0-9_+-]+){0,3}$',max_length=96)
    hour: int = Field(ge=0,le=23)
    minute: int = Field(ge=0,le=59)
    fold: Literal['EARLIEST','LATEST'] = 'EARLIEST'
    gap: Literal['NEXT_VALID_MINUTE'] = 'NEXT_VALID_MINUTE'
    grace_us: int = Field(default=3_600_000_000,ge=0,le=86_400_000_000)

    @model_validator(mode='after')
    def known_zone(self):
        try:ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError,ValueError):raise ValueError('unknown IANA timezone') from None
        return self

    def _local(self,instant):
        try:return (EPOCH+timedelta(microseconds=instant)).astimezone(ZoneInfo(self.timezone))
        except (ValueError,OverflowError):raise CoreError('CALENDAR_TIME_INVALID') from None

    def _on(self,day):
        naive=datetime(day.year,day.month,day.day,self.hour,self.minute)
        zone=ZoneInfo(self.timezone)
        # Handle even date-line shifts, with a hard finite 1-day bound.
        for shift in range(1441):
            wall=naive+timedelta(minutes=shift);choices=[]
            for fold in (0,1):
                utc=wall.replace(tzinfo=zone,fold=fold).astimezone(timezone.utc)
                if utc.astimezone(zone).replace(tzinfo=None)==wall:
                    delta=utc-EPOCH;choices.append((delta.days*86400+delta.seconds)*1_000_000+delta.microseconds)
            if choices:return min(choices) if self.fold=='EARLIEST' else max(choices)
        raise CoreError('CALENDAR_GAP_UNSUPPORTED')

    def next_after(self,instant):
        local=self._local(instant)
        for offset in range(3):
            candidate=self._on(local.date()+timedelta(days=offset))
            if candidate>instant:return candidate
        raise CoreError('CALENDAR_NEXT_UNAVAILABLE')

    def latest_due(self,instant):
        local=self._local(instant)
        for offset in range(3):
            candidate=self._on(local.date()-timedelta(days=offset))
            if candidate<=instant:return candidate
        raise CoreError('CALENDAR_PREVIOUS_UNAVAILABLE')

    def occurrence_key(self,instant):
        return digest([self.model_dump(mode='json'),self._local(instant).date().isoformat()])
