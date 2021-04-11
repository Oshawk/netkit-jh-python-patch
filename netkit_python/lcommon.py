from . import common

# Ensure the script is not being run independently.
if __name__ == "__main__":
    raise common.NetkitError("This script is not intended for standalone use.")


def lab_vhost_list(directory):
    conf = directory / "lab.conf"
    if conf.is_file():
        with conf.open() as f:
            for line in f.readlines():
                line = line.split("#")[0].strip()
                if line.startswith("machines="):
                    return line[9:].strip("\"").split()

    # TODO: Space in name checking?
    lab_vhost_list_ = []
    for candidate in directory.iterdir():
        if candidate.is_dir() and candidate.name not in ("shared", "_test", "CVS"):
            lab_vhost_list_.append(candidate.name)

    return lab_vhost_list_


def vhost_list(arguments):
    lab_vhost_list_ = lab_vhost_list(arguments.directory)

    if len(arguments.vhost_list) == 0:
        return lab_vhost_list_
    else:
        vhost_list_ = []
        for vhost in arguments.vhost_list:
            if vhost in lab_vhost_list_:
                vhost_list_.append(vhost)
            else:
                common.logger.warning(f"Machine {vhost} is not part of the lab in {arguments.directory}.")

        return vhost_list_
