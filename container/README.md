# LeTP Docker Image and Control Script

This image provides a standardized environment for running LeTP, to make it simple for users to set
up, write, and execute tests regardless of how their local host environment is configured.

While the image may be used independently, it is primarily intended to be controlled via the wrapper
script, also named `letp` and found in this directory.

## Installation

Two dependencies are required to use the image and script: Docker Engine and Python 3.  On Ubuntu,
these may be installed using `apt-get`:

```bash
sudo apt-get install docker.io python3
```

The `letp` wrapper script is self contained and may be executed from anywhere.  For convenience it
may be added to the `$PATH` environment variable, either by copying/symlinking it into an
appropriate location, or by updating `$PATH`.

For example:

```bash
mkdir -p ~/bin
ln -s ${PWD}/letp ~/bin/letp
```

## Configuration

The `letp` script searches in the current working directory, and then up through each parent
directory, for a configuration file named `letp.json`.  If this file is found, its contents are
loaded and used to override the internal defaults of the tool.  Paths in `letp.json` may be
absolute, or relative to the directory containing the file.  The following table describes the
available configuration properties.

| Field                          | Type           | Default     | Description |
| ------------------------------ | -------------- | ----------- | ----------- |
| **`image`**                    | String         | `"letp"`    | Name of the Docker image to download. Also the name to use when creating an image. |
| **`container`**                | String         | `"letp"`    | Name of the Docker container to create from the image in order to run commands. |
| **`module`**                   | String         | `"wp76xx"`  | Module name to use for test bench configuration. |
| **`build`**                    | Object         | `{}`        | Section describing parameters for building the Docker image.  Required for **letp build** but optional otherwise. |
| **`build.source`**             | String         | `""`        | Directory where the Dockerfile for the image may be found.  Required for **letp build** but optional otherwise. |
| **`build.args`**               | Object         | `{}`        | Section listing Dockerfile argument (`ARG`) override values. |
| **`build.args.LETP_VERSION`**  | String         | `"master"`  | LeTP repository version to clone for internal copy. |
| **`build.args.LETP_REMOTE`**   | String         | `"https://github.com/legatoproject/LeTP.git"` | LeTP repository remote to clone for internal copy. |
| **`build.args.TESTS_VERSION`** | String         | `"master"`  | Tests repository version to clone for internal copy. |
| **`build.args.TESTS_REMOTE`**  | String         | `"https://github.com/legatoproject/Qa-LeTP.git"` | Tests repository remote to clone for internal copy. |
| **`mount`**                    | Object         | `{}`        | Section describing the volume mounts to be attached to the container. |
| **`mount.letp`**               | String         | `""`        | External LeTP source path.  If empty, the container's internal release copy of the LeTP source (cloned from `$LETP_REMOTE` above) will be used. |
| **`mount.tests`**              | String         | `""`        | Directory containing LeTP test cases.  If empty, the container's internal release copy of the tests (cloned from `$TESTS_REMOTE` above) will be used. |
| **`mount.artifacts`**          | String         | `"./build"` | Directory containing build artifacts required by the test cases. |
| **`mount.tools`**              | String         | `""`        | Directory containing tools required for managing the test target.  If empty, the container's internal release copy of the tools will be used. |
| **`mount./*`**                 | String         | `""`        | Additional directories to mount in the container at the indicated absolute path. |
| **`serial`**                   | Object         | `{}`        | Section describing the serial devices to be attached to the container. |
| **`serial.at`**                | Object         | `""`        | External serial port to map to the container's AT device.  If empty, no `/dev/ttyAT0` device will be present in the container. |
| **`serial.cli`**               | Object         | `""`        | External serial port to map to the container's CLI device.  If empty, no `/dev/ttyCLI0` device will be present in the container. |
| **`extra_parameters`**         | Array\[String] | `[]`        | Additional parameters to pass to `docker run`.  This allows further configuration of the container environment. |

### Example Development Configuration

```json
{
    "module":     "hl7802",
    "build": {
        "source": "./letp/container"
    },
    "mount": {
        "/home/letp/legato": "./legato",
        "artifacts":         "./modem/map/build",
        "letp":              "./letp",
        "tests":             "../Legato-qa",
        "tools":             "./modem/tools"
    },
    "serial": {
        "at":     "/dev/serial/by-id/usb-FTDI_FT231X_USB_UART_DN05SPNM-if00-port0",
        "cli":    "/dev/serial/by-id/usb-FTDI_FT231X_USB_UART_DN05SG92-if00-port0"
    }
}
```

## Usage

```
usage: letp [-h] [-d] [-i IMAGE] {update,build,login,tidy,run,version} ...

LeTP test execution tool

optional arguments:
  -h, --help            show this help message and exit
  -d, --debug           enable debug logging
  -i IMAGE, --image IMAGE
                        override configuration's image name

sub-commands:
  {update,build,login,tidy,run,version}
    update              fetch the Docker image from the registry.
    build               locally (re)build the Docker image.
    login               start an interactive shell in the LeTP container.
    tidy                remove and clean up snapshot image(s).
    run                 run test(s); remaining arguments are passed to the
                        internal `letp run` command.
    version             display version of the internal letp command.
```

### Sub Commands

| Command            | Description |
| ------------------ | ----------- |
| **`letp update`**  | Fetch the LeTP Docker image from the registry. This will add or update the local Docker image named in the configuration file. |
| **`letp build`**   | Locally (re)build the Docker image.  This is intended for use developing the Docker image and its contents.  The configuration file must point to the location where the LeTP image Dockerfile is located.  The built image uses the image name specified in the configuration. |
| **`letp login`**   | Start an an interactive shell in the container.  Useful for container development or for running muliple test commands manually. |
| **`letp tidy`**    | Remove and clean up the snapshot image(s) used to persist the container state.  The next time a command is run the base image will be used as a starting point. |
| **`letp run`**     | Run an LeTP test command.  See the LeTP documentation for more details on possible parameters to `letp run`. |
| **`letp version`** | Display the version of LeTP in use within the container. |

## Behaviour

Whenever a command is issued to the wrapper script which requires execution in the container, the
following sequence of events takes place:

1.  Determine if the required image is available locally, and download it from **registry.legato**
    if it is not.
2.  Start a container instance from the image, attaching any volume mounts as required by the
    configuration.  For mounts with internal source versions, this effectively masks the internal
    copy.
3.  Execute the `letp-container-init` script in a Bash login shell session in the running container.
    This does the following:
    1.  Iterate through the "well known" source locations/volume mounts along with any additional
        mounts and:
        1.  Install any APT packages listed in the `apt-requirements.txt` file, if present in the
            root of the directory.
        2.  Install any Pip packages listed in the `requirements.txt` file, if present in the root
            of the directory.
        3.  Record the name of the "mount point" in `~/.letp/mount.txt` (regardless of whether the
            directory is an actual volume mount).
    2.  Generate `~/.letp/name.xml` containing the module name for inclusion in LeTP's
        `testbench.xml`.
    3.  Generate `~/.letp/slink1.xml` and `~/.letp/slink2.xml` containing the CLI and AT port
        properties for inclusion in LeTP's `testbench.xml`.
4.  Execute the requested command in a Bash login shell session in the container:
    1.  When the session starts, the Bash `.profile` file for the "letp" user sources
        `~/.letp/env.sh`:
        1.  Set all of the environment variables required by LeTP.
        2.  Iterate over each of the mounts listed in `~/.letp/mount.txt` and source the file
            `letp-env.sh` from the root directory of each, if present.
    2.  Run the requested command in this environment.
5.  Stop the container.
6.  Save the container state as a new working image.  This working image will be used the next time
    a command is run, unless **letp tidy** is run to clean it up.  Saving this working image speeds
    up subsequent runs as the package installations will not need to be run again.

**Note:**  The container and working image are intended to be ephemeral.  While the working image
does contain state to speed up subsequent command invocations, the cost of destroying and recreating
it is only the time and bandwidth required to reinstall the configuration-specific packages.  _Do
not store anything in the container that you are unwilling to lose._  State stored in any of the
volume mounted directories will be preserved and so that is where any work should be done that must
be saved.

## gsmMuxd

The gsmMuxd utility is included in the image to manage the creation of virtual serial ports for CMUX
support.  The source code may be obtained from https://github.com/ya-jeks/gsmmux, and built by
running `make`.  If the binary is updated, the sha256 hash for it in `contents/90-letp-user` will
also have to be updated:

```bash
openssl dgst -binary -sha256 contents/gsmMuxd | openssl base64
```
