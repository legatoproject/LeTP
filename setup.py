"""Packaging setup."""
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="LeTP",
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
    license="Mozilla Public License 2.0",
    author="Sierra Wireless Legato Team",
    author_email="LegatoQA@sierrawireless.com",
    description="Legato testing project, pexpect based CLI system testing tool.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/legatoproject/LeTP",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Mozilla Public License 2.0",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)
