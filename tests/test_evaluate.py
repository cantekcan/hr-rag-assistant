import pytest

from hr_assistant.evaluate import contains_keyword, normalize


def test_normalize_turkish_capitals():
    assert normalize("İZİN IŞIK") == "izin ışık"


@pytest.mark.parametrize("answer, keyword", [
    ("3 gün izin alırsınız", "3"),
    ("deneme süresi 2 aydır", "2 ay"),   # Turkish suffix after the keyword
    ("toplam 1,5 gün", "1,5"),
    ("on dört gün", "on dört"),
])
def test_keyword_found(answer, keyword):
    assert contains_keyword(answer, keyword)


@pytest.mark.parametrize("answer, keyword", [
    ("13 gün izin", "3"),                # part of a larger number
    ("140 saat", "14"),
    ("1,5 gün", "1"),                    # integer part of a decimal
    ("madde 5.7.5.1.3 uyarınca", "3"),   # section numbers are ignored
])
def test_keyword_not_found(answer, keyword):
    assert not contains_keyword(answer, keyword)
