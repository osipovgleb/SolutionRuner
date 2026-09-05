from pathlib import Path
import requests
from urllib.parse import parse_qs, urlparse
import argparse
import logging
import re
from . import svg_parser3


def safe_output_name(url, index=None):
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    file_id = query.get("id", [None])[0]
    if file_id:
        return file_id

    if parsed.path and "/" in parsed.path:
        candidate = parsed.path.rsplit("/", 1)[-1]
        if candidate:
            return candidate

    return f"file_{index or 1}"


def get_image(url):
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30
        )
    except Exception as exc:
        return [False, f"Не получилось получить файл: {exc}"]

    if response.status_code != 200:
        return [False, f"Ошибка доступа к ссылке (HTTP {response.status_code})"]

    return [True, response]


def _setup_logger(log_path):
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("svg_batch")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.handlers.clear()

    formatter = logging.Formatter("%(message)s")

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger


def _parse_ok_message(message):
    match = re.search(
        r"^\[(.+)\] Готово\. g: удалено=(\d+), осталось=(\d+)\. "
        r"Комментариев удалено=(\d+)\.",
        message,
    )
    if not match:
        return None

    file_id = match.group(1)
    removed_g = int(match.group(2))
    removed_comments = int(match.group(4))
    return file_id, removed_g, removed_comments


def _write_report(path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def process_links_file(links_path, output_dir, new_color, logger):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    total = 0
    ok = 0
    failed = []
    no_comments = []
    no_g_removed = []

    with open(links_path, "r", encoding="utf-8") as infile:
        for index, raw_line in enumerate(infile, start=1):
            url = raw_line.strip()
            if not url:
                continue

            total += 1
            logger.info(f"Получил ссылку #{index}: {url}")

            base_name = safe_output_name(url, index)
            out_file = output_dir / f"{base_name}_new"

            status, payload = get_image(url)
            if not status:
                logger.error(f"[ERROR] {url} -> {payload}")
                failed.append(f"{base_name}\t{url}\t{payload[1]}")
                continue

            try:
                status, message = svg_parser3.transform_svg_to_path(
                    payload.content,
                    out_file,
                    new_color,
                    file_id=base_name
                )
            except Exception as exc:
                status = False
                message = f"Ошибка внутри обработчика: {exc}"

            if status:
                ok += 1
                logger.info(f"[OK] {url} -> {message}")
                parsed = _parse_ok_message(message)
                if parsed is None:
                    logger.error(
                        f"[ERROR] {url} -> Не удалось распознать статистику ответа"
                    )
                    failed.append(f"{base_name}\t{url}\t{message}")
                    continue

                file_id, removed_g, removed_comments = parsed

                if removed_comments == 0:
                    no_comments.append(f"{file_id}\t{url}")

                if removed_g == 0:
                    no_g_removed.append(f"{file_id}\t{url}")
            else:
                logger.error(f"[ERROR] {url} -> {message}")
                failed.append(f"{base_name}\t{url}\t{message}")

    _write_report(output_dir / "failed.txt", failed)
    _write_report(output_dir / "no_comments.txt", no_comments)
    _write_report(output_dir / "no_g_removed.txt", no_g_removed)

    logger.info(
        "Справки: "
        f"failed.txt={len(failed)}, "
        f"no_comments.txt={len(no_comments)}, "
        f"no_g_removed.txt={len(no_g_removed)}"
    )

    logger.info(f"Готово. Успешно: {ok}/{total}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Преобразование набора SVG-ссылок из txt-файла."
    )
    parser.add_argument("links_txt", help="Файл со ссылками (по одной на строку)")
    parser.add_argument(
            "--out-dir",
            default="./out",
            help="Дирректория для сохранения (По умолчанию ./out)",
        )
    parser.add_argument(
        "--new-color",
        default="#143B8F",
        help="Цвет для замены (по умолчанию: #143B8F)",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help="Путь к файлу лога. По умолчанию: <out-dir>/run.log",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    output_dir = Path(args.out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    log_path = Path(args.log_file) if args.log_file else output_dir / "run.log"
    logger = _setup_logger(log_path)
    logger.info(
        f"Запуск: links_txt={args.links_txt}, out_dir={output_dir}, "
        f"new_color={args.new_color}, log_file={log_path}"
    )

    process_links_file(args.links_txt, output_dir, args.new_color, logger)


if __name__ == "__main__":
    main()
