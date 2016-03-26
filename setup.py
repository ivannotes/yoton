import re
import ast
from setuptools import setup

packages = [
    'yoton',
]

_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('yoton/__init__.py') as f:
    version = str(ast.literal_eval(
        _version_re.search(f.read().decode('utf-8')).group(1))
    )

setup(
    name='yoton',
    version=version,
    url='https://github.com/ivannotes/yoton',
    license='MIT',
    author="Ivan Lee",
    author_email='miracle.ivanlee@gmail.com',
    description='Cache decorator to make applying cache less pain',
    packages=packages,
    platforms='any',
    install_requires=[
        'redis',
    ],
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)
