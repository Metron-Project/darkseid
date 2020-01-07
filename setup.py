"""Setup file for darkseid"""
from setuptools import find_packages, setup

import darkseid

setup(
    name="darkseid",
    version=darkseid.VERSION,
    description="A library to interact with comic archives",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Brian Pepple",
    author_email="bdpepple@gmail.com",
    url="https://github.com/bpepple/darkseid",
    license="GPLv3",
    packages=find_packages(exclude=["tests"]),
    python_requires=">=3.6",
    install_requires=["natsort", "pillow"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.6",
        "Topic :: Software Development :: Libraries",
        "Topic :: Utilities",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX",
        "Operating System :: POSIX :: BSD",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
    ],
    keywords=["comics", "comic", "metadata", "tagging", "tagger"],
)
