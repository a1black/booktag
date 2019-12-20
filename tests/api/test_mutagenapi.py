import unittest.mock as mock

import pytest

from booktag.api import mutagenapi


@pytest.fixture
def id3tag():
    """Returns function for creating mock ID3 frame."""
    def builder(**kwargs):
        tag = mock.MagicMock(spec=list(kwargs.keys()))
        tag.configure_mock(**kwargs)
        return tag

    return builder


def test_split_value_where_value_is_list_expect_unpacked_list():
    data, seps = ['comma,sep', 'and&sep', 'slash/sep'], (',', '&', '/')
    value = mutagenapi.split_values(data, sep=seps)
    assert value == ['comma', 'sep', 'and', 'sep', 'slash', 'sep']
    assert mutagenapi.split_values('comma,sep', sep=seps) == ['comma', 'sep']


def test_id3read_where_no_attr_or_no_value_expect_SkipTagError(id3tag):
    with pytest.raises(mutagenapi.SkipTagError):
        assert mutagenapi.id3_read(id3tag(), attr='data')

    with pytest.raises(mutagenapi.SkipTagError):
        assert mutagenapi.id3_read(id3tag(data=[]), attr='data')


def test_id3_read_where_value_latin1_encoded_expect_decoded_frame_attribute(
        id3tag):
    attr_name, attr_value = 'text', ['âÕáâ']
    tag = id3tag(**{attr_name: attr_value, 'encoding': 0})
    decoded = mutagenapi.id3_read(tag, attr=attr_name, encoding='iso-8859-5')
    unchanged = mutagenapi.id3_read(tag, attr=attr_name)
    assert decoded == ['тест']
    assert unchanged == attr_value


def test_pair_read_where_value_is_empty_expect_nothing(id3tag):
    mp3pair, mp4pair, wavpair = id3tag(text=['']), [tuple([])], []
    for format, value in zip(('mp3', 'mp4', 'wav'),
                             (mp3pair, mp4pair, wavpair)):
        data = {}
        reader = mutagenapi.pair_read('data', 'num', 'total', format)
        reader(dict(data=value), data)
        assert data == {}


def test_pair_read_where_tag_is_set(id3tag):
    mp3pair, mp4pair, wavpair = id3tag(text=['1/2']), [(1, 2)], ['1/2']
    for format, value in zip(('mp3', 'mp4', 'wav'),
                             (mp3pair, mp4pair, wavpair)):
        target = {}
        reader = mutagenapi.pair_read('data', 'num', 'total', format)
        reader(dict(data=value), target)
        assert target == dict(num=1, total=2)


def test_pair_id3_write_where_num_and_total_are_set_expect_id3_frame():
    with mock.patch('booktag.api.mutagenapi.MP3Write.make_frame',
                    side_effect=lambda x, **kw: x):
        source, target = dict(num=1, total=2), {}
        maprule = mutagenapi.pair_id3_write('num', 'total', 'data', 'mp3')
        maprule(source, target)
        assert target == dict(data=['1/2'])


def test_pair_mp4_write_where_num_and_total_are_set_expect_mp4_frame():
    source, target = dict(num=1, total=2), {}
    maprule = mutagenapi.pair_mp4_write('num', 'total', 'data')
    maprule(source, target)
    assert target == dict(data=[(1, 2)])


def test_pair_id3_write_where_num_and_total_are_set_expect_wav_frame():
    source, target = dict(num=1, total=2), {}
    maprule = mutagenapi.pair_id3_write('num', 'total', 'data', 'wav')
    maprule(source, target)
    assert target == dict(data=['1/2'])


def test_MapRule_expect_not_none_rule_is_added():
    with mock.patch('booktag.api.mutagenapi.not_none',
                    return_value='not_none') as not_none_mock:
        mock_trans = mock.MagicMock(return_value='mock_trans')
        source, target = {'data': 'source'}, {}
        mutagenapi.MapRule('data', 'data', mock_trans).run(source, target)
        assert target == dict(data='not_none')
        mock_trans.assert_called_once_with('not_none')
        not_none_mock.assert_has_calls([mock.call('source'),
                                        mock.call('mock_trans')])


def test_MP3Read_expect_id3_read_rule_is_added():
    with mock.patch.multiple(
            'booktag.api.mutagenapi',
            not_none=mock.MagicMock(return_value='not_none'),
            id3_read=mock.MagicMock(return_value='id3_read')):
        source, target = dict(data='source'), {}
        mock_trans = mock.MagicMock(return_value='mock_trans')
        mutagenapi.MP3Read('data', 'data', mock_trans).run(source, target)
        assert target == dict(data='not_none')
        mutagenapi.id3_read.assert_called_once_with('not_none')
        mock_trans.assert_called_once_with('id3_read')
        mutagenapi.not_none.assert_has_calls([mock.call('source'),
                                              mock.call('mock_trans')])


def test_MapWriteRule_expect_append_to_list_rule():
    with mock.patch.multiple(
            'booktag.api.mutagenapi',
            not_none=mock.MagicMock(return_value='not_none'),
            to_list=mock.MagicMock(return_value='to_list')):
        source, target = dict(data='source'), {}
        mock_trans = mock.MagicMock(return_value='mock_trans')
        mutagenapi.MapWriteRule('data', 'data', mock_trans).run(source, target)
        assert target == dict(data='not_none')
        mock_trans.assert_called_once_with('not_none')
        mutagenapi.to_list.assert_called_once_with('mock_trans')
        mutagenapi.not_none.assert_has_calls([mock.call('source'),
                                              mock.call('to_list')])


@mock.patch('booktag.api.mutagenapi.MP3Write.make_frame', return_value='frame')
def test_MP3Write_expect_append_to_list_rule(mock_frame):
    with mock.patch.multiple(
            'booktag.api.mutagenapi',
            not_none=mock.MagicMock(return_value='not_none'),
            to_list=mock.MagicMock(return_value='to_list')):
        source, target = dict(data='source'), {}
        mock_trans = mock.MagicMock(return_value='mock_trans')
        mutagenapi.MP3Write('data', 'data', mock_trans).run(source, target)
        assert target == dict(data='frame')
        mock_trans.assert_called_once_with('not_none')
        mutagenapi.to_list.assert_called_once_with('mock_trans')
        mock_frame.assert_called_once_with('not_none')
        mutagenapi.not_none.assert_has_calls([mock.call('source'),
                                              mock.call('to_list')])
