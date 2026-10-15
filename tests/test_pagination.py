"""Page-number window for the shared list pager."""

import pytest

from app.ui.pagination import page_window

pytestmark = pytest.mark.no_client


def test_short_lists_show_every_page():
    assert page_window(1, 0) == []
    assert page_window(1, 1) == [1]
    assert page_window(2, 5) == [1, 2, 3, 4, 5]


def test_long_lists_collapse_with_ellipsis():
    assert page_window(1, 50) == [1, 2, 3, 4, None, 50]
    assert page_window(4, 50) == [1, None, 3, 4, 5, None, 50]
    assert page_window(50, 50) == [1, None, 47, 48, 49, 50]
