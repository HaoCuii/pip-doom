import os
import sys
from setuptools import setup, find_packages
from setuptools.command.install import install


class DoomInstall(install):
    def run(self):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from doom.game import run_game
        run_game()
        super().run()


here = os.path.dirname(os.path.abspath(__file__))

try:
    long_description = open(os.path.join(here, 'README.md'), encoding='utf-16').read()
except Exception:
    long_description = 'Play Doom in your terminal — just pip install it.'

setup(
    name='pip-doom',
    version='0.1.1',
    description='Play Doom in your terminal',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Hao Cui',
    url='https://github.com/HaoCuii/pip-doom',
    python_requires='>=3.7',
    packages=find_packages(),
    package_data={
        'doom': ['bin/*', 'doom1.wad', 'doom-ascii.cfg']
    },
    cmdclass={'install': DoomInstall},
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
)
