"""
Tutorial:
https://realpython.com/pypi-publish-python-package/

  https://setuptools.readthedocs.io/en/latest/setuptools.html#basic-use

https://python-packaging.readthedocs.io/en/latest/minimal.html

Good setup.py Example:
https://github.com/navdeep-G/setup.py
"""
"""
# install the package locally:
$ pip install .

# install the package locally using link:
$ pip install -e .

# create source distribution (sdist) archive (.gz/.zip) 
# and a wheel (.whl) for the package (in dist/ folder):
$ python setup.py sdist bdist_wheel

# build everything needed to install
# python setup.py build

# register the package on pipy
$ python setup.py register

# upload to pipy (or test.pipy):
$ twine upload --repository-url https://test.pypi.org/legacy/ dist/*

# install from test pypi:
$ pip install --index-url https://test.pypi.org/simple/ PKG
"""
import sys
import os
import pathlib
from shutil import rmtree

from setuptools import setup, Command

import vipydown

HERE = pathlib.Path(__file__).parent
#https://dbader.org/blog/write-a-great-readme-for-your-github-project
README = (HERE / "README.md").read_text()

class UploadCommand(Command):
    """Support setup.py upload."""

    description = 'Build and publish the package.'
    user_options = []

    @staticmethod
    def status(s):
        """Prints things in bold."""
        print('\033[1m{0}\033[0m'.format(s))

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        try:
            self.status('Removing previous builds…')
            rmtree(os.path.join(HERE, 'dist'))
        except OSError:
            pass

        self.status('Building Source and Wheel (universal) distribution…')
        os.system('{0} setup.py sdist bdist_wheel --universal'.format(sys.executable))

        self.status('Uploading the package to PyPI via Twine…')
        os.system('twine upload dist/*')

        self.status('Pushing git tags…')
        os.system('git tag v{0}'.format(about['__version__']))
        os.system('git push --tags')

        sys.exit()

setup(
    name=vipydown.SCRIPT_BASE,
    version=vipydown.__version__,
    description=vipydown.__doc__,
    long_description_content_type="text/markdown",
    long_description=README,
    url="https://github.com/jindrichjindrich/vipydown",
    author="Jindrich Jindrich",
    author_email="jindrich@jindrich.org",
    license="MIT",
    python_requires='>=3.6.0',
    #packages=["vipydown"],
    py_modules=['vipydown'],
    #include_package_data=True,
    install_requires=["youtube_dl"],
    ## TODO: make it usable if installed as python script with pip
    #entry_points={
    #    "console_scripts": [
    #        "vipydown=vipydown:main",
    #    ]
    #},

    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy'
    ],
    # $ setup.py publish support.
    cmdclass={
        'upload': UploadCommand,
    },
    zip_safe=False,
)
