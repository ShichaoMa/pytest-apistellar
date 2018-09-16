
def test_join_root_dir(join_root_dir):
    import os
    assert os.path.join(os.getcwd(), ".") == join_root_dir(".")
    print(join_root_dir("."))
    assert 0