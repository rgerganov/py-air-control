import setuptools
import sys

if sys.version_info < (3,4):
    sys.exit("Python 3.4 or newer is required.")

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="py-air-control",
    version="0.0.3",
    author="Radoslav Gerganov",
    author_email="rgerganov@gmail.com",
    description="Command line program for controlling Philips air purifiers",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/rgerganov/py-air-control",
    packages=['airctrl'],
    install_requires=['pycryptodome>=3.4.7'],
    entry_points={
        'console_scripts': [
            'airctrl=airctrl.airctrl:main',
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
