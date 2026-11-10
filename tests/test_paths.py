# run: python tests/test_paths.py  (or pytest)
import os
import tempfile

from meikipop.utils.paths import copy_if_missing


def test_copy_if_missing():
    with tempfile.TemporaryDirectory() as tmp:
        old, new = os.path.join(tmp, 'meikipop'), os.path.join(tmp, 'ankipop')
        copy_if_missing(old, new)  # no meikipop install: nothing to copy
        assert not os.path.exists(new)

        os.makedirs(old)
        with open(os.path.join(old, 'config.ini'), 'w') as f:
            f.write('old')
        copy_if_missing(old, new)
        with open(os.path.join(new, 'config.ini')) as f:
            assert f.read() == 'old'
        assert os.path.exists(os.path.join(old, 'config.ini'))  # copied, not moved

        with open(os.path.join(new, 'config.ini'), 'w') as f:
            f.write('new')
        copy_if_missing(old, new)  # ankipop folder already exists: never overwritten
        with open(os.path.join(new, 'config.ini')) as f:
            assert f.read() == 'new'


if __name__ == '__main__':
    test_copy_if_missing()
    print('ok')
