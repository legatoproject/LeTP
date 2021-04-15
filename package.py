"""Package management for LeTP."""
# Copyright (C) Sierra Wireless Inc.
import os
import shutil
import argparse
import hashlib


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
            os.system("python -m pip uninstall -y -r {}".format(requirement))

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

            python = "python3"

            if not shutil.which(python):
                python = "python"

            os.system("{} -m pip install --user -r {}".format(python, requirement))

            # Not failing on purpose in case the source folder is read-only
            os.mkdir(req_cache)
            open(req_hash_path, "w").close()


if __name__ == "__main__":
    args = _parse_args()

    if args.clean:
        remove_pkg(args.path)
    elif args.install:
        install_pkg(args.path)
