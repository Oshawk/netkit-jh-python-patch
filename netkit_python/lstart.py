from argparse import ArgumentParser
from multiprocessing import Process
from subprocess import call
from shlex import split
from os import getcwd
from time import sleep

from . import common, lcommon, vstart


def start(vhost, arguments):
    vstart_arguments = arguments.passthrough

    # Parse arguments from lab.conf.
    conf = arguments.directory / "lab.conf"
    if conf.is_file():
        with conf.open() as f:
            assigned = set()

            for line in f.readlines():
                line = line.strip()
                if line.startswith(f"{vhost}["):
                    line = line.split("=")
                    key = line[0].split("[")[1].split("]")[0].strip()
                    value = line[1].strip()

                    if key in assigned:
                        common.logger.warning(f"{vhost}[{key}] is assigned multiple times. Using the first assignment.")
                    else:
                        assigned.add(key)

                        if " " in value:
                            common.logger.warning(f"{vhost}[{key}]'s argument contains spaces. These will be removed.")
                            value = value.replace(" ", "")

                        if key.isdigit():
                            if not value.startswith("tap"):
                                if "," in value or "." in value:
                                    common.logger.warning(f"{vhost}[{key}]'s argument contains commas or dots. These will be removed.")
                                    value = value.replace(",", "").replace(".", "")

                            if "_" in value:
                                common.logger.warning(f"{vhost}[{key}]'s argument contains underscores. These will be removed.")
                                value = value.replace("_", "")

                            key = f"--eth{key}"
                        elif key.startswith("append"):
                            key = "--append"
                        else:
                            if len(key) == 1:
                                key = f"-{key}"
                            else:
                                key = f"--{key}"

                        vstart_arguments.append(key)

                        if len(value) > 0:
                            vstart_arguments.append(value)

    vstart_arguments.append("--hostlab")
    vstart_arguments.append(str(arguments.directory))
    vstart_arguments.append("--hostwd")
    vstart_arguments.append(str(common.resolved_directory(getcwd())))
    vstart_arguments.append("--filesystem")
    vstart_arguments.append(str(arguments.directory / f"{vhost}.disk"))
    vstart_arguments.append(vhost)

    if not arguments.verbose:
        vstart_arguments.append("-q")

    # TODO: Testing mode.

    ready = arguments.directory / f"{vhost}.ready"
    ready.unlink(missing_ok=True)

    common.logger.info(f"Generated vstart arguments: {vstart_arguments}")

    print(f"Starting: {vhost}")

    # vstart.main(vstart_arguments)

    vstart_arguments.insert(0, "vstart")
    call(vstart_arguments)

    if not arguments.fast_mode:
        while not ready.is_file():
            sleep(1)

        ready.unlink(missing_ok=True)

    sleep(arguments.grace_time)


def start_sequential(arguments):
    vhost_list = lcommon.vhost_list(arguments)
    if len(vhost_list) == 0:
        raise common.NetkitError("No machines to start.")

    for vhost in vhost_list:
        start(vhost, arguments)


def start_parallel(arguments):
    vhost_list = lcommon.vhost_list(arguments)
    if len(vhost_list) == 0:
        raise common.NetkitError("No machines to start.")

    dependency_graph = {}
    for vhost in vhost_list:
        dependency_graph[vhost] = []

    # Ensure all specified hosts and their dependencies are in the dependency graph.
    dep = arguments.directory / "lab.dep"
    if dep.is_file():
        dep_dependency_graph = {}
        with dep.open() as f:
            for line in f.readlines():
                line = line.split("#")[0].strip()
                if ":" in line:
                    line = line.split(":")
                    if len(line) >= 2:
                        dep_dependency_graph[line[0].strip()] = line[1].strip().split()

        for dependant in dependency_graph:
            if dependant in dep_dependency_graph:
                dependency_graph[dependant] = dep_dependency_graph[dependant]

        made_change = True
        while made_change:
            made_change = False
            for dependencies in tuple(dependency_graph.values()):
                for dependency in dependencies:
                    if dependency not in dependency_graph:
                        dependency_graph[dependency] = dep_dependency_graph.get(dependency, [])
                        made_change = True

    common.logger.info(f"Dependency graph: {dependency_graph}")

    # A BFS to ensure the dependency graph is acyclic. Not very efficient.
    for start_node in dependency_graph:
        queue = [start_node]
        visited = []

        while len(queue) != 0:
            current = queue.pop(0)

            if current in visited:
                raise common.NetkitError("The dependency graph is not acyclic.")

            visited.append(current)

            for node in dependency_graph[current]:
                queue.append(node)

    # Start the hosts making sure that dependencies are started first.
    max_processes = common.config["MAX_SIMULTANEOUS_VMS"] if arguments.parallel is None else arguments.parallel
    processes = {}
    while len(dependency_graph) != 0 or len(processes) != 0:
        for dependant, dependencies in dependency_graph.items():
            if dependant in processes:  # We are already processing this dependant.
                continue

            can_process = True
            for dependency in dependencies:
                if dependency in dependency_graph:
                    can_process = False
                    break

            if can_process:
                process = Process(target=start, args=(dependant, arguments))
                processes[dependant] = process
                process.start()

            if max_processes != 0 and len(processes) >= max_processes:
                break

        len_processes = len(processes)
        while len(processes) == len_processes:
            sleep(1)
            for dependant in tuple(processes):
                if not processes[dependant].is_alive():
                    del dependency_graph[dependant]
                    del processes[dependant]


def main(arguments=None):
    # TODO: Test mode.
    # TODO: Check what makefile does.

    parser = ArgumentParser(prog="lstart", description="The command used to start a Netkit lab.")

    parser.add_argument("-d", default=common.resolved_directory(getcwd()), type=common.resolved_directory, metavar="DIRECTORY", dest="directory")
    # TODO: Tmux attached and detached.
    parser.add_argument("-F", "--force-lab", action="store_true", dest="force")
    parser.add_argument("-f", "--fast", action="store_true", dest="fast_mode")
    parser.add_argument("-l", "--list", action="store_true", dest="list_vm")
    parser.add_argument("--makefile", action="store_true", dest="make_file")
    parser.add_argument("-o", "--pass", default=[], type=split, metavar="OPTIONS", dest="passthrough")  # TODO: How do we handle passthrough?

    startup_mode_group = parser.add_mutually_exclusive_group()
    startup_mode_group.add_argument("-p", type=common.unsigned_integer, metavar="VALUE", dest="parallel")
    startup_mode_group.add_argument("-s", "--sequential", action="store_true", dest="sequential")

    parser.add_argument("-v", "--verbose", action="store_true", dest="verbose")
    parser.add_argument("--version", action="store_true", dest="show_version")
    parser.add_argument("-w", "--wait", default=0, type=common.unsigned_integer, metavar="SECONDS", dest="grace_time")
    parser.add_argument("-S", "--script-mode", action="store_true", dest="script_mode")
    parser.add_argument("-R", "--rebuild-signature", action="store_true", dest="create_signature")
    parser.add_argument("--verify", choices=("user", "builtin", "both"), metavar="TESTTYPE", dest="verify")
    parser.add_argument(nargs="*", metavar="MACHINE-NAME", dest="vhost_list")

    arguments = parser.parse_args(args=arguments)

    common.verbose(arguments.verbose)

    common.logger.info(f"lstart arguments: {arguments}")

    # TODO: Warnings.

    conf_present = (arguments.directory / "lab.conf").is_file()
    dep_present = (arguments.directory / "lab.dep").is_file()

    if not conf_present and not dep_present and not arguments.force:
        raise common.NetkitError("This does not appear to be a lab directory. Use option -F to convince me it is.")

    # TODO: Update stuff.
    # TODO: Lab info printing.

    if (dep_present and not arguments.sequential) or arguments.parallel is not None:
        start_parallel(arguments)
    else:
        start_sequential(arguments)


if __name__ == "__main__":
    main()
