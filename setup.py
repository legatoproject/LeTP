"""Packaging setup."""
import pathlib

import pkg_resources
import setuptools

HERE = pathlib.Path(__file__).parent
README = (HERE / "README.md").read_text()


with pathlib.Path("requirements.txt").open() as requirements_txt:
    install_requires = [
        str(requirement)
        for requirement in pkg_resources.parse_requirements(requirements_txt)
    ]

setuptools.setup(
    name="pytest-letp",
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
    license="Mozilla Public License 2.0",
    author="Sierra Wireless Legato Team",
    author_email="LegatoQA@sierrawireless.com",
    description="Legato testing project, pexpect based CLI system testing tool.",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/legatoproject/LeTP",
    packages=setuptools.find_packages(exclude=("test/*",)),
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Mozilla Public License 2.0",
        "Operating System :: OS Independent",
    ],
    install_requires=install_requires,
    python_requires=">=3.6",
    entry_points={"console_scripts": ["letp=letp.__main__:main"]},
)
