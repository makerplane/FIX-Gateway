import setuptools

with open("README.rst", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="fixgw",
    version="0.0.1",
    author="Phil Birkelbach",
    author_email="phil@petrasoft.net",
    description="FIX-Gateway: Gateway software for the Flight Information eXchange protocols",
    long_description=long_description,
    #long_description_content_type="text/x-rst",
    url="https://github.com/pypa/sampleproject",
    packages=setuptools.find_packages(),
    #packages=['canfix'],
    #package_data = {'fixgw':['config/*']},
    install_requires = ['pyyaml',],
    #test_suite = 'tests',
    #scripts = ['bin/fixgw', 'bin/fixgwc'],
    entry_points = {
        'console_scripts': ['fixgw=fixgw.server:main', 'fixgwc=fixgw.client:main'],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)"
        "Operating System :: POSIX :: Linux",
    ],
)
