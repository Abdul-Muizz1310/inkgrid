from collections.abc import Callable

import pytest

import pdf_factory

DETERMINISTIC = {k: v for k, v in pdf_factory.OPENABLE.items() if k != "owner_only"}


@pytest.mark.parametrize("make", DETERMINISTIC.values(), ids=DETERMINISTIC.keys())
def test_fixture_bytes_are_deterministic(make: Callable[[], bytes]) -> None:
    assert make() == make()


def test_encrypted_fixtures_are_listed_as_salted() -> None:
    assert pdf_factory.encrypted() != pdf_factory.encrypted()
