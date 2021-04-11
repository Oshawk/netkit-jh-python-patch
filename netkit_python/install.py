from shutil import copyfile

from . import common

source_directory = common.resolved_file(__file__).parent

print("Making install directory.")
install_directory = common.netkit_home / "netkit_python"
install_directory.mkdir(mode=0o775, exist_ok=True)

print("Copying files:")
for source_file in source_directory.iterdir():
    destination_file = install_directory / source_file.name
    print(f"  Copying {source_file} to {destination_file}.")
    copyfile(source_file, destination_file)

print("Making wrapper scripts:")
wrapper_directory = common.netkit_home / "bin"
for wrapper in ("lstart",):
    wrapper_file = wrapper_directory / f"python-{wrapper}"
    print(f"  Making: {wrapper_file}")
    wrapper_file.unlink(missing_ok=True)
    wrapper_file.touch(mode=0o775)
    wrapper_file.write_text(f"""#!/bin/sh\n\nPYTHONPATH="$(dirname "$0")/.." python3 -m netkit_python.{wrapper} "$@"\n""")

