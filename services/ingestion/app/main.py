import signal
import sys
from .poller import Poller
from .logging_config import setup_logging

def main():
    setup_logging()
    poller = Poller()
    
    def handle_shutdown(signum, frame):
        poller.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    poller.start()

if __name__ == "__main__":
    main()
