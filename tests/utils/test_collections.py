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
