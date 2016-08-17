import os

from bears.documentation.DocumentationStyleBear import DocumentationStyleBear
from tests.LocalBearTestHelper import verify_local_bear


def load_testfile(test, filename):
    filepath = os.path.join(os.path.dirname(__file__), "test_files",
                            "DocumentationStyleBear", filename)
    with open(filepath) as fl:
        return fl.read()


good_file = load_testfile("DocumentationStyleBear", "good_file.py.test")
good_file_empty = load_testfile("DocumentationStyleBear", "good_file2.py.test")

bad_file = load_testfile("DocumentationStyleBear", "bad_file.py.test")
file_sameline = load_testfile("DocumentationStyleBear", "bad_file2.py.test")

DocumentationStyleBear = verify_local_bear(DocumentationStyleBear,
                                           valid_files=(good_file,
                                                        good_file_empty),
                                           invalid_files=(bad_file,
                                                          file_sameline),
                                           settings={'language': 'python',
                                                     'docstyle': 'default'})
