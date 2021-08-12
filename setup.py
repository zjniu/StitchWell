from setuptools import setup,find_packages

VERSION = "2.0"
DESCRIPTION = "ND2 Stitcher"
LONG_DESCRIPTION = "A pure Python implementation for bulk stitching ND2 files."

setup(
    name="stitchwell",
    version=VERSION,
    author="William Niu",
    author_email="<wniu721@gmail.com>",
    description=DESCRIPTION,
    long_description_content_type="text/markdown",
    long_description=LONG_DESCRIPTION,
    packages=find_packages(),
    install_requires=['nd2reader','numpy','scikit-image','tifffile','tqdm'],
    keywords=["python","ND2","stitch"],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python :: 3",
        "Operating System :: Unix",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
    ]
)