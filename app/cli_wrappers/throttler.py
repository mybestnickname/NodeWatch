import asyncio
import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any

QUEUE_MAX_LEN = 30

logger = logging.getLogger(__name__)


class QueueIsFullException(Exception):
    pass


class Throttler:
    """Bound the concurrency of (potentially blocking) tasks.

    Tasks are submitted to a bounded queue and processed by a fixed pool of
    worker coroutines. Synchronous callables run in a thread pool so they never
    block the event loop. Submissions are rejected when the queue is full and
    can be given an execution timeout.
    """

    def __init__(self, max_concurrent_tasks: int = 1, queue_maxlen: int = QUEUE_MAX_LEN) -> None:
        self._max_concurrent_tasks = max_concurrent_tasks
        self.queue_maxlen = queue_maxlen

        self._executor: ThreadPoolExecutor | None = None
        self._queue: asyncio.Queue | None = None
        self._workers: list[asyncio.Task] = []
        self._workers_started = False

    async def start_workers(self) -> None:
        """Create the queue, thread pool and worker coroutines (idempotent)."""
        if self._workers_started:
            return
        logger.debug(
            "Starting throttler: max_concurrent_tasks=%s queue_maxlen=%s",
            self._max_concurrent_tasks,
            self.queue_maxlen,
        )
        self._executor = ThreadPoolExecutor(max_workers=self._max_concurrent_tasks)
        self._queue = asyncio.Queue(maxsize=self.queue_maxlen)
        self._workers = [asyncio.create_task(self._worker()) for _ in range(self._max_concurrent_tasks)]
        self._workers_started = True

    async def _worker(self) -> None:
        """Process tasks from the queue until cancelled."""
        assert self._queue is not None
        while True:
            func, args, kwargs, future = await self._queue.get()
            try:
                if future.cancelled():
                    continue  # the caller already gave up (e.g. timed out)
                try:
                    if asyncio.iscoroutinefunction(func):
                        result = await func(*args, **kwargs)
                    else:
                        loop = asyncio.get_running_loop()
                        result = await loop.run_in_executor(self._executor, partial(func, *args, **kwargs))
                    if not future.cancelled():
                        future.set_result(result)
                except Exception as exc:  # noqa: BLE001 - surface any task error to the caller
                    logger.error("Error while processing task: %s", exc)
                    if not future.cancelled():
                        future.set_exception(exc)
            except asyncio.CancelledError:
                raise
            finally:
                self._queue.task_done()

    async def run_task(
        self,
        func: Callable,
        *args: Any,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> Any | None:
        """Submit a task and await its result.

        Raises :class:`QueueIsFullException` if the queue is full. Returns
        ``None`` if the task does not complete within ``timeout`` seconds.
        """
        if self._queue is None:
            raise RuntimeError("Throttler workers have not been started.")
        if self._queue.full():
            logger.error("Queue is full. Task will not be added.")
            raise QueueIsFullException("queue is full")

        future = asyncio.get_running_loop().create_future()
        await self._queue.put((func, args, kwargs, future))

        try:
            if timeout:
                return await asyncio.wait_for(future, timeout)
            return await future
        except asyncio.TimeoutError:
            logger.error("Task execution timed out after %ss.", timeout)
            future.cancel()
            return None

    def shutdown(self) -> None:
        """Cancel workers and shut down the thread pool."""
        for worker in self._workers:
            worker.cancel()
        self._workers = []
        self._workers_started = False
        if self._executor:
            self._executor.shutdown(wait=False)
            self._executor = None

    def __del__(self) -> None:
        try:
            self.shutdown()
        except Exception:  # pragma: no cover - best-effort cleanup during GC
            pass
