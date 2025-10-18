from types import SimpleNamespace
from datetime import datetime, timedelta

from core.utilities import calendar_overlap_utility as cou


def make_appt(subject, start, end, **kwargs):
    a = SimpleNamespace()
    a.subject = subject
    a.start_time = start
    a.end_time = end
    for k, v in kwargs.items():
        setattr(a, k, v)
    return a


def test_merge_duplicates():
    start = datetime(2025, 10, 18, 9)
    end = datetime(2025, 10, 18, 10)
    a1 = make_appt('A', start, end)
    a2 = make_appt('A', start, end)  # duplicate
    a3 = make_appt('B', start, end)

    merged = cou.merge_duplicates([a1, a2, a3])
    # a1 and a2 should be deduplicated
    subjects = {getattr(x, 'subject') for x in merged}
    assert subjects == {'A', 'B'}
    assert len(merged) == 2


def test_detect_overlaps_and_metadata():
    # Create 3 appointments where first two overlap, third separate
    s1 = datetime(2025, 10, 18, 9)
    e1 = datetime(2025, 10, 18, 10)
    s2 = datetime(2025, 10, 18, 9, 30)
    e2 = datetime(2025, 10, 18, 11)
    s3 = datetime(2025, 10, 18, 12)
    e3 = datetime(2025, 10, 18, 13)

    a1 = make_appt('X', s1, e1, show_as='busy', importance='normal', sensitivity='normal')
    a2 = make_appt('Y', s2, e2, show_as='busy', importance='high', sensitivity='private')
    a3 = make_appt('Z', s3, e3, show_as='free', importance='low', sensitivity='normal')

    overlaps = cou.detect_overlaps([a1, a2, a3])
    # Expect one overlap group containing a1 and a2
    assert len(overlaps) == 1
    group = overlaps[0]
    assert a1 in group and a2 in group and a3 not in group

    meta = cou.detect_overlaps_with_metadata([a1, a2, a3])
    assert len(meta) == 1
    entry = meta[0]
    assert entry['metadata']['group_size'] == 2
    assert entry['metadata']['show_as_values'] == ['busy', 'busy']
    assert entry['metadata']['importance_values'] == ['normal', 'high']
    assert entry['metadata']['sensitivity_values'] == ['normal', 'private']

