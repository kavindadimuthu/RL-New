"""Temporarily prevent automatic Windows idle sleep during active benchmarks.

No global power-plan changes, display request, away mode, or GPU settings.
Call on the same thread for entry/exit. Explicit user sleep is not overridden.
"""
from contextlib import contextmanager
import ctypes
import os

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001


@contextmanager
def keep_awake(enabled=True, setter=None):
    """Request system availability for this scope; restore prior thread flags."""
    if not enabled or (os.name != 'nt' and setter is None):
        yield {'requested': False, 'reason': 'disabled_or_not_windows'}
        return
    if setter is None:
        setter = ctypes.WinDLL('kernel32', use_last_error=True).SetThreadExecutionState
        setter.argtypes = [ctypes.c_uint]
        setter.restype = ctypes.c_uint
    previous = setter(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
    if previous == 0:
        raise OSError('Windows did not accept the temporary sleep-prevention request')
    try:
        yield {'requested': True, 'previous_flags': previous,
               'flags': ES_CONTINUOUS | ES_SYSTEM_REQUIRED}
    finally:
        # Restore the calling thread's previous requirements, including when
        # the benchmark raises. Do not leave a persistent sleep request.
        if setter(previous | ES_CONTINUOUS) == 0:
            raise OSError('Could not restore previous Windows execution-state flags')
