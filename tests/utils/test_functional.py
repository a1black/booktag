import unittest.mock as mock

import pytest

from booktag.utils import functional


def test_rstrip_where_all_items_true_expect_list_copy():
    function = mock.MagicMock(return_value=True)
    data = list(range(10))
    striped = functional.rstrip(data, function)
    assert striped == data
    assert striped is not data
    assert function.call_count == 1


def test_rstrip_where_all_items_false_expect_empty_list():
    function = mock.MagicMock(return_value=False)
    data = list(range(10))
    striped = functional.rstrip(data, function)
    assert striped == []
    assert striped is not data
    assert function.call_count == len(data)


def test_rstrip_where_false_items_on_both_ends_expect_right_trimmed():
    data = [False, False, True, False, False]
    striped = functional.rstrip(data)
    assert striped == [False, False, True]


def test_lstrip_where_all_items_true_expect_list_copy():
    function = mock.MagicMock(return_value=True)
    data = list(range(10))
    striped = functional.lstrip(data, function)
    assert striped == data
    assert striped is not data
    assert function.call_count == 1


def test_lstrip_where_all_items_false_expect_empty_list():
    function = mock.MagicMock(return_value=False)
    data = list(range(10))
    striped = functional.lstrip(data, function)
    assert striped == []
    assert striped is not data
    assert function.call_count == len(data)


def test_lstrip_where_false_items_on_both_ends_expect_left_trimmed():
    data = [False, False, True, False, False]
    striped = functional.lstrip(data)
    assert striped == [True, False, False]
