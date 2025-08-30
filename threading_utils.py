from PyQt5.QtCore import QObject, pyqtSignal, QRunnable

class WorkerSignals(QObject):
    done = pyqtSignal(object)
    error = pyqtSignal(str)

class CallableWorker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.sig = WorkerSignals()

    def run(self):
        try:
            res = self.fn(*self.args, **self.kwargs)
            self.sig.done.emit(res)
        except Exception as e:
            self.sig.error.emit(str(e))
