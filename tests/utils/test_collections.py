import unittest.mock as mock

import pytest

from booktag.utils import collections


def test_attrdict_where_key_accessed_as_attributes():
    data = collections.attrdict()
    data.attribute = 'attribute'
    assert data.attribute == data['attribute']

    del data.attribute
    assert 'attribute' not in data

    with pytest.raises(AttributeError):
        assert data.attribute


def test_FiltrableDict_expect_filter_applied_on_setitem():
    filters = dict(key=mock.MagicMock())
    dct = collections.FiltrableDict(filters, {'key': 1}, key=2)
    dct['key'] = 3
    dct['nokey'] = 4
    assert filters['key'].call_count == 3
    filters['key'].assert_has_calls(
        [mock.call(1), mock.call(2), mock.call(3)])


def test_PropDict_expect_execute_callable_on_getitem():
    callval = mock.MagicMock(return_value='iscallable')
    dct = collections.PropDict(callval=callval, noncallval='notcallable')
    assert dct['noncallval'] == 'notcallable'
    assert dct['callval'] == 'iscallable'
    callval.assert_called_once_with()
