import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Optional

QUEUE_MAX_LEN = 30

logger = logging.getLogger(__name__)


class QueueIsFullException(Exception):
    pass


class Throttler:
    def __init__(self, max_concurrent_tasks: int = 1, queue_maxlen: int = QUEUE_MAX_LEN):
        self._max_concurrent_tasks = max_concurrent_tasks
        self.queue_maxlen = queue_maxlen

        self._executor = None
        self._queue = None
        self._workers_started = False
        self._tasks_in_queue = []

    async def start_workers(self):
        """Создание очереди, пула и запуск воркеров для обработки задач"""
        logger.debug(
            "Throttler is running... "
            f"max_conc_tasks: {self._max_concurrent_tasks} queue_maxlen: {self.queue_maxlen}."
        )
        if not self._executor:
            self._executor = ThreadPoolExecutor()

        if not self._queue:
            self._queue = asyncio.Queue(maxsize=self.queue_maxlen)

        if not self._workers_started:
            for _ in range(self._max_concurrent_tasks):
                # Создание воркеров в текущем цикле
                asyncio.create_task(self._worker())
            self._workers_started = True

    async def _worker(self):
        """Обработка задач из очереди"""
        while True:
            try:
                if self._queue.empty():
                    await asyncio.sleep(0.1)
                    continue

                func, args, kwargs, future = await self._queue.get()

                if future.cancelled():
                    continue  # Если задача была отменена, пропускаем её

                try:
                    if asyncio.iscoroutinefunction(func):
                        # если корутина, то вызываем асинхронно
                        result = await func(*args, **kwargs)
                    else:
                        # синхронную в пуле потоков
                        loop = asyncio.get_event_loop()
                        result = await loop.run_in_executor(self._executor, lambda: func(*args, **kwargs))
                    future.set_result(result)
                except Exception as e:
                    logger.error(f"Error while processing task: {e}")
                    future.set_exception(e)
                finally:
                    self._queue.task_done()
            except asyncio.CancelledError:
                break  # Завершаем работу воркера при отмене задачи
            except Exception as e:
                logger.error(f"Unexpected error in worker: {e}")

    async def run_task(
        self,
        func: Callable,
        *args: Any,
        timeout: Optional[float] = None,
        **kwargs: Any
    ) -> Optional[Any]:
        """
        Запуск задачи с контролем очереди и возможностью задания таймаута.
        Если очередь заполнена, то ошибка.
        Если не успели выполнить за timeout, возвращает None.
        """
        if self._queue.full():
            logger.error("Queue is full. Task will not be added.")
            raise QueueIsFullException("queue is full")

        future = asyncio.get_running_loop().create_future()
        await self._queue.put((func, args, kwargs, future))
        self._tasks_in_queue.append(future)

        try:
            if timeout:
                return await asyncio.wait_for(future, timeout)
            else:
                return await future
        except asyncio.TimeoutError:
            logger.error("task execution timed out.")
            future.cancel()  # отмена при таймауте
            return None

    def shutdown(self):
        """Закрытие пула потоков"""
        if self._executor:
            self._executor.shutdown(wait=True)

    def __del__(self):
        self.shutdown()
