from argparse import ArgumentParser, SUPPRESS
from ipaddress import AddressValueError, IPv4Address
from os import getcwd
from pathlib import Path
from shlex import split
from shutil import which
from time import sleep

from . import common, vcommon

TERMINAL_APPLICATION_MAPPER = {
    "konsole-tab": "konsole",
    "gnome": "gnome-terminal",
    "wsl": "wsl.exe",
    "wt": "wt.exe",
}

TERMINAL_KERNEL_COMMAND_MAPPER = {
    None: "null",
    "this": "fd:0,fd:1",
    "this_noporthelper": "fd:0,fd:1",
}

TERMINAL_SETUP_MAPPER = {
    "konsole": "konsole,-T,-e",
    "konsole-tab": f"""{common.netkit_home / "bin" / "konsole-tabs.sh"},-T,-e""",
    "gnome": "xterm=gnome-terminal,-t,-x",

}


def interface_error(_):
    raise common.NetkitError("--ethN is an invalid option. N should be replaced with the interface number.")


class InterfaceType:
    def __init__(self, interface):
        self.interface = interface

    def invoke(self, argument):
        if argument == "":
            raise common.NetkitError(f"--{self.interface}'s argument is empty. This is not allowed.)")

        if "_" in argument:
            raise common.NetkitError(f"--{self.interface}'s argument contains underscores. This is not allowed.")

        if argument.startswith("tap") and ("," in argument or "." in argument):
            raise common.NetkitError(f"--{self.interface}'s argument contains commas or dots. This is not allowed.")

        return self.interface, argument


def memory(argument):
    unsigned_integer = common.unsigned_integer(argument)

    if not (common.config["MIN_MEM"] <= unsigned_integer <= common.config["MAX_MEM"]):
        raise common.NetkitError("--mem's argument is outside of the allowed range.")

    return unsigned_integer


def model_file_system(argument):
    file = common.resolved_file(argument)

    if "," in str(file):
        raise common.NetkitError("The model file system's path can't contain commas.")

    return file


def file_system(argument):
    file = Path(argument).resolve()

    if "," in str(file):
        raise common.NetkitError("The file system's path can't contain commas.")

    return file


def interfaces(arguments, kernel_command):
    if not arguments.quiet:
        print("Interfaces:")

    enabled_default_route = False
    hubs = []
    for interface, hub in arguments.interfaces:
        if hub == "tap":
            raise common.NetkitError("Invalid tap collision domain.")

        if hub.startswith("tap,"):
            hub = hub.split(",")

            try:
                assert len(hub) == 3
                tap = IPv4Address(hub[1])
                guest = IPv4Address(hub[2])
            except (AddressValueError, AssertionError):
                raise common.NetkitError("Invalid tap collision domain.")

            hub = "tap"
        else:
            tap = None
            guest = None

        socket = common.config["HUB_SOCKET_DIR"] / f"""{common.config["HUB_SOCKET_PREFIX"]}_{common.user_id}_{hub}{common.config["HUB_SOCKET_EXTENSION"]}"""

        if not arguments.quiet:
            print(f"  {interface}@{hub}: {socket}")

        kernel_command.append(f"{interface}=daemon,,,{socket}")

        if tap is not None:
            hubs.append((socket, tap, guest))
            kernel_command.append(f"autoconf_{interface}={guest}")

            if not enabled_default_route:
                kernel_command.append(f"def_route={tap}")
                enabled_default_route = True
        else:
            hubs.append(socket)

    return hubs


def wake_up_port_helper_(arguments):
    sleep(5)
    vcommon.run_command(("uml_mconsole", arguments.vhost, "help"), background=True, silent=True)


def remove_file_system_(arguments):
    while not arguments.file_system.is_file():
        sleep(1)

    arguments.file_system.unlink()


def run_kernel_command(kernel_command, wake_up_port_helper, remove_file_system, hubs, arguments):
    if wake_up_port_helper:
        vcommon.run_function(wake_up_port_helper_, (arguments,))

    if remove_file_system:
        vcommon.run_function(remove_file_system_, (arguments,))

    vcommon.run_command(kernel_command, arguments, background=False, silent=False)


def main(arguments=None):
    parser = ArgumentParser(prog="lstart", description="The command used to start a Netkit virtual machine.")

    # Matching arguments by prefix is not supported so we have to do something a little hacky.
    parser.add_argument("--ethN", type=interface_error, metavar="DOMAIN", dest="dummy")
    for i in range(common.config["MAX_INTERFACES"]):
        parser.add_argument(f"--eth{i}", action="append", default=[], type=InterfaceType(f"eth{i}").invoke, help=SUPPRESS, dest="interfaces")

    parser.add_argument("-k", "--kernel", default=common.config["VM_KERNEL"], type=common.resolved_file, metavar="FILENAME", dest="kernel")
    parser.add_argument("-M", "--mem", default=common.config["VM_MEMORY"], type=memory, metavar="MEMORY", dest="memory")
    parser.add_argument("-m", "--model-fs", default=common.config["VM_MODEL_FS"], type=model_file_system, metavar="MODEL-FILESYSTEM", dest="model_file_system")
    parser.add_argument("-f", "--filesystem", type=file_system, metavar="FILESYSTEM", dest="file_system")
    parser.add_argument("--con0", default=common.config["VM_CON0"], type=common.optional, metavar="MODE", dest="con0")
    parser.add_argument("--con1", default=common.config["VM_CON1"], type=common.optional, metavar="MODE", dest="con1")
    parser.add_argument("-e", "--exec", metavar="COMMAND", dest="exec")
    parser.add_argument("-l", "--hostlab", type=common.resolved_directory, metavar="DIRECTORY", dest="host_lab")
    parser.add_argument("-w", "--hostwd", type=common.resolved_directory, metavar="DIRECTORY", dest="host_working_directory")
    parser.add_argument("--append", default=[], type=split, metavar="PARAMETER", dest="append")

    tmux_group = parser.add_mutually_exclusive_group()
    tmux_group.add_argument("--tmux-attached", action="store_const", const=True, default=common.config["TMUX_OPEN_TERMS"], dest="tmux_open_terminals")
    tmux_group.add_argument("--tmux-detached", action="store_const", const=False, default=common.config["TMUX_OPEN_TERMS"], dest="tmux_open_terminals")

    parser.add_argument("-F", "--foreground", action="store_true", dest="foreground")
    parser.add_argument("-H", "--no-hosthome", action="store_true", dest="no_host_home")
    parser.add_argument("-W", "--no-cow", action="store_true", dest="use_model_file_system")
    parser.add_argument("-D", "--hide-disk-file", action="store_true", dest="remove_file_system")
    parser.add_argument("-q", "--quiet", action="store_true", dest="quiet")
    parser.add_argument("-p", "--print", action="store_true", dest="print")
    parser.add_argument("-v", "--verbose", action="store_true", dest="verbose")
    parser.add_argument("--debug", action="store_true", dest="debug")
    parser.add_argument("--xterm", default=common.config["TERM_TYPE"], choices=("konsole", "konsole-tab", "gnome", "xterm", "alacritty", "kitty", "wsl", "wt"), metavar="TYPE", dest="terminal")
    parser.add_argument("--version", action="store_true", dest="version")
    # TODO: Testing stuff.
    parser.add_argument(metavar="MACHINE-NAME", dest="vhost")

    arguments = parser.parse_args(args=arguments)

    if arguments.con0 == "this" and arguments.con1 == "this":
        raise common.NetkitError("Only one console can be attached to the current terminal.")

    if arguments.use_model_file_system and arguments.file_system is not None:
        raise common.NetkitError("The arguments (-W / --no-cow) and (-f / --filesystem) are mutually exclusive.")

    if arguments.use_model_file_system and arguments.remove_file_system:
        raise common.NetkitError("The arguments (-W / --no-cow) and (-D / --hide-disk-file) are mutually exclusive.")

    for argument in (arguments.con0, arguments.con1):
        if not (argument in ("xterm", "this", "pty", None) or argument.startswith("port:")):
            raise common.NetkitError("Unrecognised con device.")

    common.verbose(arguments.verbose)

    common.logger.info(f"vstart arguments: {arguments}")

    if arguments.con0 == "xterm" or arguments.con1 == "xterm" or (arguments.con0 == "tmux" and arguments.tmux_open_terminals):
        terminal_application = arguments.terminal

        if terminal_application in TERMINAL_APPLICATION_MAPPER:
            terminal_application = TERMINAL_APPLICATION_MAPPER[terminal_application]

        if which(terminal_application) is None:
            raise common.NetkitError("The specified terminal application was not found. Please install it.")

    if arguments.file_system is None:
        arguments.file_system = common.resolved_directory(getcwd()) / f"{arguments.vhost}.disk"

    kernel_command = [arguments.kernel]

    # TODO: File system checking.

    if not arguments.quiet:
        print(f"Starting: {arguments.vhost}")
        print(f"Kernel: {arguments.kernel}")

    modules = arguments.kernel.parent / "modules"
    if modules.is_dir():
        kernel_command.append(f"modules={modules}")
        if not arguments.quiet:
            print(f"Modules: {modules}")

    kernel_command.append(f"name={arguments.vhost}")
    kernel_command.append(f"title={arguments.vhost}")
    kernel_command.append(f"umid={arguments.vhost}")

    kernel_command.append(f"""mem={arguments.memory + common.config["VM_MEMORY_SKEW"]}M""")
    print(f"Memory: {arguments.memory}")

    if arguments.use_model_file_system:
        kernel_command.append(f"ubd0={arguments.model_file_system}")
        arguments.file_system = arguments.model_file_system
    else:
        kernel_command.append(f"ubd0={arguments.file_system},{arguments.model_file_system}")

    if not arguments.quiet:
        print(f"Model file system: {arguments.model_file_system}")
        print(f"File system: {arguments.file_system}")

    kernel_command.append("root=98:0")

    hubs = interfaces(arguments, kernel_command)

    if not arguments.no_host_home:
        kernel_command.append(f"hosthome={common.home}")

    if not arguments.print and common.pid(arguments.vhost, common.user_id) is not None:
        raise common.NetkitError(f"{arguments.vhost} is already running.")

    if not arguments.print and common.in_use(arguments.file_system):
        raise common.NetkitError(f"The file system is being used by another process.")

    if arguments.exec is not None:
        kernel_command.append(f"exec=\"{arguments.exec}\"")
        if not arguments.quiet:
            print(f"Boot command: {arguments.exec}")

    if arguments.host_lab is not None:
        kernel_command.append(f"hostlab={arguments.host_lab}")
        if not arguments.quiet:
            print(f"Host lab: {arguments.host_lab}")

    if arguments.host_working_directory is not None:
        kernel_command.append(f"hostwd={arguments.host_working_directory}")
        if not arguments.quiet:
            print(f"Host working directory: {arguments.host_working_directory}")

    if arguments.debug:
        kernel_command.insert(0, "--args")
        kernel_command.insert(0, "gdb")
    elif not arguments.verbose:
        kernel_command.append("quiet")

    if arguments.con0 == "xterm" and not common.config["CON0_PORTHELPER"]:
        arguments.con0 = "this_noporthelper"

    for con, argument in zip(("con0", "con1"), (arguments.con0, arguments.con1)):
        terminal_kernel_command = argument

        if terminal_kernel_command in TERMINAL_KERNEL_COMMAND_MAPPER:
            terminal_kernel_command = TERMINAL_KERNEL_COMMAND_MAPPER[terminal_kernel_command]

        kernel_command.append(f"{con}={terminal_kernel_command}")

    kernel_command.append("SELINUX_INIT=0")

    if arguments.terminal in TERMINAL_SETUP_MAPPER:
        kernel_command.append(f"xterm={TERMINAL_SETUP_MAPPER[arguments.terminal]}")

    kernel_command += arguments.append
    if len(arguments.append ) > 0 and not arguments.quiet:
        print(f"Additional arguments: {arguments.append}")

    if arguments.con0 in ("xterm", "this_noporthelper"):
        kernel_command.insert(0, arguments.vhost)
        kernel_command.insert(0, arguments.terminal)
        kernel_command.insert(0, common.netkit_home / "bin" / "block-wrapper")  # TODO: Use a block wrapper script.

    if arguments.con0 == "tmux":
        if which("tmux") is None:
            raise common.NetkitError("tmux is not installed.")

        kernel_command.insert(0, arguments.vhost)
        kernel_command.insert(0, "tmux")
        kernel_command.insert(0, common.netkit_home / "bin" / "block-wrapper")  # TODO: Use a block wrapper script.

    vcommon.run_hubs(hubs, arguments)

    background = not arguments.foreground and arguments.con0 != "this" and arguments.con1 != "this"
    silent = arguments.con0 is None
    wake_up_port_helper = common.config["CON0_PORTHELPER"]
    remove_file_system = arguments.remove_file_system

    print(kernel_command)

    vcommon.run_function(run_kernel_command, (kernel_command, wake_up_port_helper, remove_file_system, hubs, arguments), background=background, silent=silent)


if __name__ == "__main__":
    main()
