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

setup(
    name='pip-doom',
    version='0.1.0',
    packages=find_packages(),
    package_data={
        'doom': ['bin/*', 'doom1.wad', 'doom-ascii.cfg']
    },
    cmdclass={'install': DoomInstall},
)