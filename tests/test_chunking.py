from hr_assistant.ingest import Section, build_chunks
from hr_assistant.retrieval import split_chunk

SECTIONS = [
    Section("5", "5. ÇALIŞMA KOŞULLARI", page=3),  # heading only, too short to index
    Section("5.7", "5.7. İzinler: çalışanların kullanabileceği izin türleri aşağıdadır.", page=4),
    Section("5.7.4", "5.7.4. Yıllık izin: en az bir yıl çalışmış olanlara yıllık izin verilir.", page=4),
]


def test_short_headings_are_skipped():
    assert [c.section for c in build_chunks(SECTIONS)] == ["5.7", "5.7.4"]


def test_chunk_text_starts_with_parent_path():
    chunk = build_chunks(SECTIONS)[1]
    assert chunk.text == "5. ÇALIŞMA KOŞULLARI > 5.7. İzinler\n" + SECTIONS[2].text
    assert chunk.page == 4


def test_split_chunk_round_trip():
    chunk = build_chunks(SECTIONS)[1]
    assert split_chunk(chunk.text) == ("5. ÇALIŞMA KOŞULLARI > 5.7. İzinler", SECTIONS[2].text)


def test_split_chunk_without_path():
    assert split_chunk("1. Amaç ve kapsam metni") == ("", "1. Amaç ve kapsam metni")
