from contextlib import redirect_stderr, redirect_stdout
from multiprocessing import Process
from os import fork
from time import sleep

from . import common

# Ensure the script is not being run independently.
if __name__ == "__main__":
    raise common.NetkitError("This script is not intended for standalone use.")


def run_command_(command):
    # TODO
    pass


def run_command(command, arguments, background=True, silent=True):
    if not arguments.quiet:
        print(f"Running command: {command}")

    run_function(run_command_, (command,), background=background, silent=silent)


class MutedFunction:
    def __init__(self, function):
        self.function = function

    def invoke(self, *args, **kwargs):
        with redirect_stdout(None):
            with redirect_stderr(None):
                self.function(*args, **kwargs)


class DoubleForkedFunction:
    def __init__(self, function):
        self.function = function

    def invoke(self, *args, **kwargs):
        if fork() == 0:  # Child.
            self.function(*args, **kwargs)
        else:  # Parent.
            return


def run_function(function, args, background=True, silent=True):
    if silent:
        function = MutedFunction(function).invoke

    if background:
        function = DoubleForkedFunction(function).invoke
        process = Process(target=function, args=args)
        process.start()
        process.join()
    else:
        function(*args)


def run_inet_hub(hub, tap, guest, arguments):
    # TODO
    pass


def run_hub(hub, arguments):
    # TODO: Logging?
    if not hub.is_socket() or not common.in_use(hub):
        run_command(("uml_switch", "-hub", "-unix", hub), arguments)

    while not arguments.print and not hub.is_socket():
        sleep(1)


def run_hubs(hubs, arguments):
    for hub in hubs:
        if isinstance(hub, tuple):
            run_inet_hub(*hub, arguments)
        else:
            run_hub(hub, arguments)
