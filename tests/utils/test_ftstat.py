import unittest.mock as mock

import pytest

from booktag.utils import ftstat


def test_ft_mode_where_path_does_not_exists_expect_FileNotFoundError():
    with pytest.raises(FileNotFoundError):
        assert ftstat.ft_mode('/none/existing/path')


def test_ft_mode_where_path_to_block_device_expect_zero_moe():
    with mock.patch('os.path.exists', return_value=True):
        with mock.patch('os.path.isfile', return_value=False):
            assert ftstat.ft_mode('/test/path') == 0


def test_ft_mode_where_path_to_directory():
    with mock.patch('os.path.exists', return_value=True):
        with mock.patch('os.path.isdir', return_value=True):
            mode = ftstat.ft_mode('/test/path')
            assert ftstat.S_ISDIR(mode)
            assert ftstat.S_IFCT(mode) == 0
            assert ftstat.S_IFFF(mode) == 0


def test_ft_mode_where_path_is_symlink():
    with mock.patch('os.path.exists', return_value=True):
        with mock.patch('os.path.islink', return_value=True):
            mode = ftstat.ft_mode('/test/path')
            assert ftstat.S_ISLNK(mode)
            assert ftstat.S_IFCT(mode) == 0
            assert ftstat.S_IFFF(mode) == 0


def test_ft_mode_where_path_is_regular_file():
    with mock.patch('magic.from_file', return_value='plain/text'):
        with mock.patch('os.path.exists', return_value=True):
            with mock.patch('os.path.isfile', return_value=True):
                mode = ftstat.ft_mode('/test/path')
                assert ftstat.S_ISREG(mode)
                assert ftstat.S_IFCT(mode) == 0
                assert ftstat.S_IFFF(mode) == 0


@pytest.mark.parametrize('mime', [
    'mpeg', 'x-mpeg', 'mp2', 'mp3', 'x-mp2', 'x-mp3'])
def test_ft_mode_where_path_to_mp3_file(mime):
    with mock.patch('magic.from_file', return_value='audio/{0}'.format(mime)):
        with mock.patch('os.path.exists', return_value=True):
            with mock.patch('os.path.isfile', return_value=True):
                mode = ftstat.ft_mode('/test/path')
                assert ftstat.S_ISREG(mode)
                assert ftstat.S_ISAUD(mode)
                assert ftstat.S_ISMP3(mode)


@pytest.mark.parametrize('mime', [
    'm4a', 'mp4', 'mpeg4', 'x-m4a', 'x-mp4', 'x-mpeg4'])
def test_ft_mode_where_path_to_mp4_file(mime):
    with mock.patch('magic.from_file', return_value='audio/{0}'.format(mime)):
        with mock.patch('os.path.exists', return_value=True):
            with mock.patch('os.path.isfile', return_value=True):
                mode = ftstat.ft_mode('/test/path')
                assert ftstat.S_ISREG(mode)
                assert ftstat.S_ISAUD(mode)
                assert ftstat.S_ISMP4(mode)


def test_ft_mode_where_path_to_ogg_file():
    with mock.patch('magic.from_file', return_value='audio/ogg'):
        with mock.patch('os.path.exists', return_value=True):
            with mock.patch('os.path.isfile', return_value=True):
                mode = ftstat.ft_mode('/test/path')
                assert ftstat.S_ISREG(mode)
                assert ftstat.S_ISAUD(mode)
                assert ftstat.S_ISOGG(mode)


@pytest.mark.parametrize('mime', ['wav', 'x-wav'])
def test_ft_mode_where_path_to_wav_file(mime):
    with mock.patch('magic.from_file', return_value='audio/{0}'.format(mime)):
        with mock.patch('os.path.exists', return_value=True):
            with mock.patch('os.path.isfile', return_value=True):
                mode = ftstat.ft_mode('/test/path')
                assert ftstat.S_ISREG(mode)
                assert ftstat.S_ISAUD(mode)
                assert ftstat.S_ISWAV(mode)


def test_ft_mode_where_path_to_jpeg_file():
    with mock.patch('magic.from_file', return_value='image/jpeg'):
        with mock.patch('os.path.exists', return_value=True):
            with mock.patch('os.path.isfile', return_value=True):
                mode = ftstat.ft_mode('/test/path')
                assert ftstat.S_ISREG(mode)
                assert ftstat.S_ISIMG(mode)
                assert ftstat.S_ISJPG(mode)


def test_ft_mode_where_path_to_png_file():
    with mock.patch('magic.from_file', return_value='image/png'):
        with mock.patch('os.path.exists', return_value=True):
            with mock.patch('os.path.isfile', return_value=True):
                mode = ftstat.ft_mode('/test/path')
                assert ftstat.S_ISREG(mode)
                assert ftstat.S_ISIMG(mode)
                assert ftstat.S_ISPNG(mode)


def test_ft_mode_where_path_to_fb2_file():
    with mock.patch('magic.from_file', return_value='application/fb2+xml'):
        with mock.patch('os.path.exists', return_value=True):
            with mock.patch('os.path.isfile', return_value=True):
                mode = ftstat.ft_mode('/test/path')
                assert ftstat.S_ISREG(mode)
                assert ftstat.S_ISBOK(mode)
                assert ftstat.S_ISFB2(mode)


def test_ft_mode_where_path_to_epub_file():
    with mock.patch('magic.from_file', return_value='application/epub+zip'):
        with mock.patch('os.path.exists', return_value=True):
            with mock.patch('os.path.isfile', return_value=True):
                mode = ftstat.ft_mode('/test/path')
                assert ftstat.S_ISREG(mode)
                assert ftstat.S_ISBOK(mode)
                assert ftstat.S_ISEPB(mode)


def test_ft_mode_where_path_to_pdf_file():
    with mock.patch('magic.from_file', return_value='application/pdf'):
        with mock.patch('os.path.exists', return_value=True):
            with mock.patch('os.path.isfile', return_value=True):
                mode = ftstat.ft_mode('/test/path')
                assert ftstat.S_ISREG(mode)
                assert ftstat.S_ISBOK(mode)
                assert ftstat.S_ISPDF(mode)
