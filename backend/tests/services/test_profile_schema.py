import pydantic
import pytest

from app.schemas.user import ProfileUpdateIn


def test_only_sent_fields_are_reported_and_name_is_trimmed():
    body = ProfileUpdateIn(name="  Ann ")
    assert body.model_dump(exclude_unset=True) == {"name": "Ann"}


def test_username_is_passed_through_untouched_for_the_service_to_normalize():
    body = ProfileUpdateIn(username="  MoStAfA ")
    assert body.model_dump(exclude_unset=True) == {"username": "  MoStAfA "}


@pytest.mark.parametrize(
    "payload",
    [{}, {"name": None}, {"username": None}, {"name": "   "}, {"name": "x" * 61}],
)
def test_bad_bodies_are_rejected(payload):
    with pytest.raises(pydantic.ValidationError):
        ProfileUpdateIn(**payload)