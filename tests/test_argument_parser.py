import pytest

from custom_argument_parser import CustomArgumentParser


def create_parser():
    """
    Создаёт экземпляр парсера аргументов командной строки.

    Returns:
        CustomArgumentParser: Настроенный парсер с обязательным
        позиционным аргументом URL.
    """
    parser = CustomArgumentParser(
        description='Тестирование скорости загрузки по протоколу HTTP',
        usage='%(prog)s <URL>'
    )

    parser.add_argument(
        'url',
        help='URL для скачивания'
    )

    return parser


def test_parser_accepts_url():
    """
    Проверяет корректное получение URL из аргументов командной строки.
    """

    parser = create_parser()

    args = parser.parse_args([
        'https://example.com/file'
    ])

    assert args.url == 'https://example.com/file'


def test_parser_requires_url(capsys):
    """
    Проверяет обязательность передачи URL.

    Проверяет код завершения программы и сообщение об ошибке,
    выводимое в stderr при отсутствии URL.
    """

    parser = create_parser()

    with pytest.raises(SystemExit) as error:
        parser.parse_args([])

    assert error.value.code == 2

    captured = capsys.readouterr()

    assert 'укажите URL для загрузки' in captured.err
