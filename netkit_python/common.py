from base64 import b64decode
import logging
from pathlib import Path
from pwd import getpwnam, getpwuid
from subprocess import check_output
from os import environ, geteuid


class NetkitError(RuntimeError):
    pass


# Ensure the script is not being run independently.
if __name__ == "__main__":
    raise NetkitError("This script is not intended for standalone use.")


# Make logging look a little nicer. The log level can be changed later.
logging.basicConfig(format="[%(levelname)s] %(message)s")

# Get the module level logger.
logger = logging.getLogger(__name__)


# Determines if a file is in use by another process.
def in_use(path):
    path = path.resolve()

    for candidate in Path("/proc").iterdir():
        if candidate.name.isdigit() and candidate.is_dir():
            candidate /= "fd"
            try:
                for candidate_ in candidate.iterdir():
                    if path == candidate_.resolve():
                        return True
            except PermissionError:
                pass

    return False


def optional(string):
    if string == "none":
        return None

    return string


# Determines the pid of a running lab.
def pid(vhost, user=None):
    if user is not None:
        user = getpwnam(user).pw_uid

    for candidate in Path("/proc").iterdir():
        if candidate.name.isdigit() and candidate.is_dir() and (user is None or candidate.stat().st_uid == user):
            candidate /= "cmdline"
            if candidate.is_file() and f"umid={vhost} " in candidate.read_text():
                return int(candidate.parent.name)


def resolved_file(string):
    path = Path(string).resolve()

    if not path.is_file():
        raise NetkitError("The path must be a file.")

    return path


def resolved_directory(string):
    path = Path(string).resolve()

    if not path.is_dir():
        raise NetkitError("The path must be a directory.")

    return path


def unsigned_integer(string):
    integer = int(string)

    if integer < 0:
        raise NetkitError("The integer must be greater than or equal to 0.")

    return integer


def verbose(verbose_):
    if verbose_:
        logger.setLevel(level=logging.INFO)


# Get the Netkit home from NETKIT_HOME or the legacy VLAB_HOME.
netkit_home = None
for environment_variable in ("NETKIT_HOME", "VLAB_HOME"):
    try:
        netkit_home = resolved_directory(environ[environment_variable])
        break
    except KeyError:
        pass

if netkit_home is None:
    raise NetkitError("The NETKIT_HOME environment variable is not properly set.")

# Load the configuration. To reduce complexity a shell script is used.
config = {}
for line in check_output(("/bin/sh", netkit_home / "netkit_python" / "load_config.sh", netkit_home)).decode().split("\n"):
    line = line.strip().split()

    if len(line) >= 2:
        config[line[0]] = b64decode(line[1]).decode()[:-1]  # Strip out the "\n" appended by echo.

# Convert integer arguments.
for key in ("VM_MEMORY", "VM_MEMORY_SKEW", "MAX_INTERFACES", "MIN_MEM", "MAX_MEM", "MAX_SIMULTANEOUS_VMS", "GRACE_TIME", "UPDATE_CHECK_PERIOD"):
    config[key] = int(config[key])

# Convert boolean arguments.
for key in ("CON0_PORTHELPER", "USE_SUDO", "TMUX_OPEN_TERMS", "CHECK_FOR_UPDATES"):
    config[key] = config[key] == "yes"

# Convert directory arguments. They do not have to exist.
for key in ("MCONSOLE_DIR", "HUB_SOCKET_DIR"):
    config[key] = Path(config[key]).resolve()

# Convert file arguments. These should exist.
for key in ("VM_MODEL_FS", "VM_KERNEL"):
    config[key] = resolved_file(config[key])

# Convert optionals.
for key in ("VM_CON0", "VM_CON1"):
    config[key] = optional(config[key])

user_id = getpwuid(geteuid()).pw_name
home = resolved_directory(environ["HOME"])
