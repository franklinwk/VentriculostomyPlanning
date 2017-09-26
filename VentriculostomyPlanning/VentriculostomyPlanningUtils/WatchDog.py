from qt import QTimer
import qt
class WatchDog:
    def __init__(self, timeout, userHandler=None):  # timeout in seconds
        self.timeout = timeout
        self.handler = userHandler if userHandler is not None else self.defaultHandler
        self.timer = qt.QTimer()
        self.timer.timeout.connect(self.handler)

    def reset(self):
        self.timer.stop()
        self.timer.start(self.timeout*1000)

    def stop(self):
        self.timer.stop()

    def defaultHandler(self):
        print "time out"
        raise self