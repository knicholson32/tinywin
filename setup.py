import setuptools
with open("README.md", "r") as fh:
    long_description = fh.read()
setuptools.setup(
    name='tinywin',
    version='0.1.10',
    scripts=[],
    author="Keenan Nicholson",
    author_email="",
    description="A tiny Curses window management library, designed to work with CircuitPython_Curses",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/knicholson32/tinywin/",
    packages=setuptools.find_packages(),
    classifiers=[
         "Programming Language :: Python :: 3",
         "License :: OSI Approved :: MIT License",
         "Operating System :: Unix",
         "Environment :: Console :: Curses"
    ],
)
