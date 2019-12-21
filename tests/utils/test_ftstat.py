import stat
import unittest.mock as mock

import pytest

from booktag.utils import ftstat


@pytest.fixture
def stat_res():
    """Returns function for creating mock ID3 frame."""
    def builder(st_mode):
        res = mock.MagicMock(spec=['st_mode'])
        res.configure_mock(st_mode=st_mode)
        return res

    return builder


def test_ft_mode_where_path_does_not_exists_expect_FileNotFoundError():
    with pytest.raises(FileNotFoundError):
        assert ftstat.ft_mode('/none/existing/path')


def test_ft_mode_where_path_neither_file_nor_directory_expect_zero(stat_res):
    assert ftstat.ft_mode('/test/path', stat_res(stat.S_IFBLK)) == 0


def test_ft_mode_where_path_to_directory(stat_res):
    mode = ftstat.ft_mode('/test/path', stat_res(stat.S_IFDIR))
    assert ftstat.S_ISDIR(mode)
    assert ftstat.S_IFCT(mode) == 0
    assert ftstat.S_IFFF(mode) == 0


def test_ft_mode_where_path_is_symlink(stat_res):
    mode = ftstat.ft_mode('/test/path', stat_res(stat.S_IFLNK))
    assert ftstat.S_ISLNK(mode)
    assert ftstat.S_IFCT(mode) == 0
    assert ftstat.S_IFFF(mode) == 0


def test_ft_mode_where_path_is_regular_file(stat_res):
    with mock.patch('magic.from_file', return_value='plain/text'):
        mode = ftstat.ft_mode('/test/path', stat_res(stat.S_IFREG))
        assert ftstat.S_ISREG(mode)
        assert ftstat.S_IFCT(mode) == 0
        assert ftstat.S_IFFF(mode) == 0


@pytest.mark.parametrize('mime', [
    'mpeg', 'x-mpeg', 'mp2', 'mp3', 'x-mp2', 'x-mp3'])
def test_ft_mode_where_path_to_mp3_file(stat_res, mime):
    with mock.patch('magic.from_file', return_value='audio/{0}'.format(mime)):
        mode = ftstat.ft_mode('/test/path', stat_res(stat.S_IFREG))
        assert ftstat.S_ISREG(mode)
        assert ftstat.S_ISAUD(mode)
        assert ftstat.S_ISMP3(mode)


@pytest.mark.parametrize('mime', [
    'm4a', 'mp4', 'mpeg4', 'x-m4a', 'x-mp4', 'x-mpeg4'])
def test_ft_mode_where_path_to_mp4_file(stat_res, mime):
    with mock.patch('magic.from_file', return_value='audio/{0}'.format(mime)):
        mode = ftstat.ft_mode('/test/path', stat_res(stat.S_IFREG))
        assert ftstat.S_ISREG(mode)
        assert ftstat.S_ISAUD(mode)
        assert ftstat.S_ISMP4(mode)


def test_ft_mode_where_path_to_ogg_file(stat_res):
    with mock.patch('magic.from_file', return_value='audio/ogg'):
        mode = ftstat.ft_mode('/test/path', stat_res(stat.S_IFREG))
        assert ftstat.S_ISREG(mode)
        assert ftstat.S_ISAUD(mode)
        assert ftstat.S_ISOGG(mode)


@pytest.mark.parametrize('mime', ['wav', 'x-wav'])
def test_ft_mode_where_path_to_wav_file(stat_res, mime):
    with mock.patch('magic.from_file', return_value='audio/{0}'.format(mime)):
        mode = ftstat.ft_mode('/test/path', stat_res(stat.S_IFREG))
        assert ftstat.S_ISREG(mode)
        assert ftstat.S_ISAUD(mode)
        assert ftstat.S_ISWAV(mode)


def test_ft_mode_where_path_to_jpeg_file(stat_res):
    with mock.patch('magic.from_file', return_value='image/jpeg'):
        mode = ftstat.ft_mode('/test/path', stat_res(stat.S_IFREG))
        assert ftstat.S_ISREG(mode)
        assert ftstat.S_ISIMG(mode)
        assert ftstat.S_ISJPG(mode)


def test_ft_mode_where_path_to_png_file(stat_res):
    with mock.patch('magic.from_file', return_value='image/png'):
        mode = ftstat.ft_mode('/test/path', stat_res(stat.S_IFREG))
        assert ftstat.S_ISREG(mode)
        assert ftstat.S_ISIMG(mode)
        assert ftstat.S_ISPNG(mode)


def test_ft_mode_where_path_to_fb2_file(stat_res):
    with mock.patch('magic.from_file', return_value='application/fb2+xml'):
        mode = ftstat.ft_mode('/test/path', stat_res(stat.S_IFREG))
        assert ftstat.S_ISREG(mode)
        assert ftstat.S_ISBOK(mode)
        assert ftstat.S_ISFB2(mode)


def test_ft_mode_where_path_to_epub_file(stat_res):
    with mock.patch('magic.from_file', return_value='application/epub+zip'):
        mode = ftstat.ft_mode('/test/path', stat_res(stat.S_IFREG))
        assert ftstat.S_ISREG(mode)
        assert ftstat.S_ISBOK(mode)
        assert ftstat.S_ISEPB(mode)


def test_ft_mode_where_path_to_pdf_file(stat_res):
    with mock.patch('magic.from_file', return_value='application/pdf'):
        mode = ftstat.ft_mode('/test/path', stat_res(stat.S_IFREG))
        assert ftstat.S_ISREG(mode)
        assert ftstat.S_ISBOK(mode)
        assert ftstat.S_ISPDF(mode)
