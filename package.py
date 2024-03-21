"""Package management for LeTP."""
import os
import shutil
import argparse
import hashlib

__copyright__ = "Copyright (C) Sierra Wireless Inc."


def _parse_args():
    """Parse user arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--clean",
        "-c",
        action="store_true",
        help="Remove the required packages for LeTP",
    )
    parser.add_argument(
        "--install",
        "-i",
        action="store_true",
        help="Install the required packages for LeTP",
    )
    parser.add_argument(
        "--path", "-p", default=os.getcwd(), help="Path to the LeTP root"
    )

    return parser.parse_args()


def _get_python_cmd():
    """Determine the python cmd and return the compatible one."""
    python = "python3"

    if not shutil.which(python) or not os.system(f"{python} --version") == 0:
        python = "python"

    return python


def remove_pkg(letp_path=None):
    """Remove the required packages for LeTP."""
    if letp_path:
        req_cache = os.path.join(letp_path, ".requirements")
        python_cache = os.path.join(letp_path, "__pycache__")
        requirement = os.path.join(letp_path, "requirements.txt")

        if os.path.isdir(req_cache):
            shutil.rmtree(req_cache)

        if os.path.isdir(python_cache):
            shutil.rmtree(python_cache)

        if os.path.exists(requirement):
            os.system(
                "{} -m pip uninstall -y -r {}".format(_get_python_cmd(), requirement)
            )

        print("Packages were removed")


def install_pkg(letp_path=None):
    """Install the required packages for LeTP."""
    if letp_path:
        requirement = os.path.join(letp_path, "requirements.txt")
        req_cache = os.path.join(letp_path, ".requirements")
        if os.path.exists(requirement):
            # make a hash object
            req_hash = hashlib.sha1()

            # open file for reading in binary mode
            with open(requirement, "rb") as file:
                # loop till the end of the file
                chunk = 0
                while chunk != b"":
                    # read only 1024 bytes at a time
                    chunk = file.read(1024)
                    req_hash.update(chunk)
            req_hash = req_hash.hexdigest()
            req_hash_path = os.path.join(req_cache, req_hash)

            if os.path.exists(req_cache) and os.path.exists(req_hash_path):
                return

            print("LeTP dependencies: install {}".format(requirement))

            os.system(
                "{} -m pip install --user -r {}".format(_get_python_cmd(), requirement)
            )

            # Not failing on purpose in case the source folder is read-only
            os.makedirs(req_cache, exist_ok=True)
            open(req_hash_path, "w").close()


if __name__ == "__main__":
    args = _parse_args()

    if args.clean:
        remove_pkg(args.path)
    elif args.install:
        install_pkg(args.path)
