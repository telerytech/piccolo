from __future__ import annotations

import asyncio
import typing as t
from concurrent.futures import ThreadPoolExecutor


def run_sync(coroutine: t.Coroutine):
    """
    Run the coroutine synchronously - trying to accommodate as many edge cases
    as possible.

     1. When called within a coroutine.
     2. When called from `python -m asyncio`, or iPython with %autoawait
        enabled, which means an event loop may already be running in the
        current thread.

    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        return asyncio.run(coroutine)
    else:
        if loop.is_running():
            new_loop = asyncio.new_event_loop()

            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    new_loop.run_until_complete, coroutine
                )
                return future.result()
        else:
            return loop.run_until_complete(coroutine)
