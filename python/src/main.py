import logging
import hydra
from omegaconf import DictConfig
from threading import Thread
import signal
from functools import partial

from messaging import PikaConsumer

LOG_FORMAT = "%(asctime)s [%(levelname)s]|%(threadName)s|%(taskName)s|%(funcName)s : %(message)s"

logger = logging.getLogger(__name__)

def handle_signal(signum, frame, threadPool:list[Thread]) -> None:
    logger.info("received signal %s(%s)",signal.Signals(signum).name, signum)
    for thread in threadPool:
        thread.stop()

def joinThreads(threadPool:list[Thread],timeout:float) -> None:
    activeThread = len(threadPool)
    while activeThread > 0:
        activeThread = 0
        for thread in threadPool:
            if thread.is_alive():
                logger.debug("Thread %s still active, waiting for %d sec...", thread.name, timeout)
                activeThread += 1
                thread.join(timeout)
    logger.info("All threads stopped.")

@hydra.main(config_path="../resources", config_name="config")
def main(config:DictConfig) -> None:
    """
    Keep the main thread running until all child thread completed.
    """
    logger.info("Start main....")
    try:
        pikaConsumer: PikaConsumer = PikaConsumer(config)
        threadPool:list[Thread] = [pikaConsumer]
        signal.signal(signal.SIGTERM, partial(handle_signal, threadPool=threadPool))
        
        pikaConsumer.start()
        joinThreads(threadPool,5)
    except KeyboardInterrupt:
        logger.info("main() interrupted by keyboard...")
        pikaConsumer.stop()
    finally:
        joinThreads(threadPool,1)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    main()
