# Verified source navigation

`src/nana_core/continuity/recurrence.py:43`

Symbol: `RecurrenceSpec.next_after`

Source SHA256: e7f08c9b9666037af49b35b48bee46ae9e780e7b63a322b7f5ee97f4d5b7dc13

```python
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
```

Coverage: at most 12 lines, not a full-function or behavioral correctness proof.
