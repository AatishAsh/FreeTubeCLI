from setuptools import setup, find_packages

setup(
    name="freetube-cli",
    version="1.0.0",
    author="Aatish",
    description="A minimalist YouTube CLI for terminal-based ad-free viewing.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/freetube-cli",
    packages=find_packages(),
    install_requires=[
        "yt-dlp",
        "rich",
        "requests",
        "pillow"
    ],
    entry_points={
        "console_scripts": [
            "freetube-cli=freetubecli.freetube:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)
