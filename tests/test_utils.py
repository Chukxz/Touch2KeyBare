import pytest
from mapper_module.utils import is_in_circle, is_in_rect, rotate_resolution


def test_is_in_circle():
    # Test point exactly on the center
    assert is_in_circle(px=5, py=5, cx=5, cy=5, r=10) == True
    # Test point well within the radius
    assert is_in_circle(px=7, py=7, cx=5, cy=5, r=10) == True
    # Test point way outside the radius
    assert is_in_circle(px=20, py=20, cx=5, cy=5, r=10) == False


def test_is_in_rect():
    # Test point inside the bounds
    assert is_in_rect(px=10, py=10, left=0, right=20, top=0, bottom=20) == True
    # Test point outside the bounds
    assert is_in_rect(px=25, py=10, left=0, right=20, top=0, bottom=20) == False


def test_rotate_resolution():
    # Test standard landscape rotation (rotation 1)
    w, h = rotate_resolution(1920, 1080, 1)
    assert w == 1080
    assert h == 1920
