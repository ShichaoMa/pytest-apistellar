from file.file import File


def mock_load(filename="通过工厂mock"):
    return File(filename)


data = dict(a=5, b=8)