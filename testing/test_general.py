# pylint: disable=invalid-name, missing-class-docstring, missing-function-docstring

import os
import subprocess
from create_example_page import *

class TestGeneral:
    def test_example_file_created(self):
        test_data()
        args = ['git', 'diff', '--exit-code', 'Examples.md']
        fileChanges = subprocess.Popen(args, stdout=subprocess.PIPE)
        fileChanges.stdout.close()
        fileChanges.wait()

        if fileChanges.returncode > 0:
            raise Exception("run 'python3 create_example_page.py' to recreate Examples.md and check in the result!")