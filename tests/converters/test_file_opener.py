"""An individual bad SVG must not prevent later links from being processed."""

from types import SimpleNamespace
from unittest.mock import Mock

from solution_runner.converters import file_opener


def test_batch_records_parser_failure_and_continues(tmp_path, monkeypatch):
    links = tmp_path / "links.txt"
    links.write_text(
        "https://example.test/first.svg\nhttps://example.test/second.svg\n"
    )
    monkeypatch.setattr(
        file_opener,
        "get_image",
        lambda url: (True, SimpleNamespace(content=url.encode())),
    )
    converter = Mock(
        side_effect=[
            RuntimeError("parser failed"),
            (
                True,
                "[second] Готово. g: удалено=1, осталось=0. Комментариев удалено=1.",
            ),
        ]
    )
    monkeypatch.setattr(file_opener.svg_parser3, "transform_svg_to_path", converter)
    logger = Mock()

    file_opener.process_links_file(links, tmp_path / "out", "#143B8F", logger)

    assert converter.call_count == 2
    failed = (tmp_path / "out" / "failed.txt").read_text()
    assert "https://example.test/first.svg" in failed
    assert "Ошибка внутри обработчика: parser failed" in failed
    assert "https://example.test/second.svg" not in failed
