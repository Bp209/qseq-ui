import threading
import time
import logging
import copy

logger = logging.getLogger(__name__)


class DataCacheThread(threading.Thread):
    """A data cache thread is an object which fetches some data in the
    background and stores it locally for faster access. On startup the data is
    fetched once and after that, it is fetched again after the user has
    collected the previous value.

    Additionally, the fetched data is tagged with a timestamp and the duration
    which was needed to acquire the complete dataset.

    To use this class, override the method aquire_data().

    If halt_on_errors is set to True any exception in aquire_data() will be
    reraised. Otherwise, only an error is logged.
    """

    def __init__(self):
        threading.Thread.__init__(self)
        self.stop_request = False
        self.lock = threading.Lock()
        self.halt_on_errors = False
        self.dataset = None
        self.event = threading.Event()

    def stop(self):
        """Requests a termination of the thread and waits for it."""
        self.stop_request = True
        self.event.set()
        self.join()

    def aquire_data(self):
        """Aquires the data.

        This is the main method you have to override. It is supposed to return
        the fetched data.
        """
        raise RuntimeError('You have to override this method.')

    def cleanup(self):
        """This method is called when just before the thread exists."""
        pass

    def run(self):
        while not self.stop_request:
            start_time = time.time()
            try:
                data = self.aquire_data()
            except KeyboardInterrupt:
                raise
            except Exception:  # as e
                data = None
                logger.exception('Exception while fetching data')
                if self.halt_on_errors:
                    raise
            end_time = time.time()

            timestamp = start_time
            duration = end_time - start_time

            self.lock.acquire()
            self.dataset = (timestamp, duration, data)
            self.fetchcount = 0
            self.lock.release()

            # now wait until data is collected
            self.event.wait()
            self.event.clear()
        self.cleanup()

    def _get_data(self):
        self.lock.acquire()
        if self.dataset is None:
            dataset = None
            fetchcount = None
        else:
            fetchcount = self.fetchcount
            self.fetchcount += 1
            dataset = copy.deepcopy(self.dataset)
        self.lock.release()
        self.event.set()

        return (fetchcount, dataset)

    def get_data(self):
        """Returns the last fetched data.

        Data will be a deep copy of the original data because the object itself
        may be modified by the cache thread.

        If the data was fetched multiple times a warning is logged.

        If no data was acquired yet, None will be returned.
        """
        (fetchcount, dataset) = self._get_data()
        if fetchcount > 0:
            logger.warning('Fetch the same data multiple times')
        if dataset is None:
            return None
        else:
            return dataset[2]

    def get_data_extended(self):
        """Returns a tuple of the form (fetchcount, timestamp, duration,
        dataset).

        See get_data() for more details.
        """
        (fetchcount, dataset) = self._get_data()

        if fetchcount is not None:
            dataset = (fetchcount,) + dataset
            if fetchcount > 0:
                logger.warning('Fetch the same data multiple times')

        return dataset
