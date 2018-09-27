class File(object):

    def __init__(self, filename):
        self.filename = filename

    @classmethod
    def load(cls):
        return File(filename="这个文件是从数据库获取的")

    @classmethod
    async def load_async(cls):
        return File(filename="这个文件是从数据库获取的")
