from urllib.error import HTTPError, URLError

import pytest

import benchmark

"""
Тесты модуля benchmark.py.

Проверяют:
- Выполнение десяти последовательных HTTP GET-запросов.
- Полное чтение тела каждого HTTP-ответа.
- Корректное закрытие HTTP-ответов.
- Подсчёт времени и объёма загруженных данных.
- Обработку HTTP-ошибок и сетевых исключений.
- Расчёт статистических показателей.
- Валидацию результатов тестирования скорости загрузки.
"""


class FakeResponse:
    """
    Имитация HTTP-ответа для изолированного тестирования.

    Позволяет проверять чтение данных блоками и закрытие ответа
    без выполнения реальных HTTP-запросов.

    Attributes:
        chunks: Последовательность блоков данных, возвращаемых при чтении.
        closed: Признак закрытия HTTP-ответа.
        read_calls: Список размеров блоков, переданных в метод read().
    """

    def __init__(self, chunks: list[bytes]):
        self.chunks = iter(chunks)
        self.closed = False
        self.read_calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.closed = True

    def read(self, size: int) -> bytes:
        self.read_calls.append(size)
        return next(self.chunks, b'')


def test_run_benchmark_downloads_ten_responses(monkeypatch):
    """
    Проверяет выполнение десяти последовательных HTTP-запросов.

    Проверяет полное чтение ответов, корректное закрытие соединений,
    измерение времени и подсчёт загруженных данных.
    """

    responses = [
        FakeResponse([b'abc', b'def'])
        for _ in range(benchmark.REQUEST_COUNT)
    ]

    opened_responses = []

    def fake_urlopen(url, timeout):
        # Предыдущий ответ должен быть закрыт до следующего запроса.
        if opened_responses:
            assert opened_responses[-1].closed is True

        response = responses[len(opened_responses)]
        opened_responses.append(response)

        assert url == 'https://example.com/file'
        assert timeout == benchmark.TIMEOUT

        return response

    monkeypatch.setattr(benchmark, 'urlopen', fake_urlopen)
    monkeypatch.setattr(benchmark, 'print_progress', lambda *args: None)
    monkeypatch.setattr(benchmark, 'finish_progress', lambda: None)

    # Каждый запрос занимает ровно одну секунду.
    monkeypatch.setattr(
        benchmark.time,
        'perf_counter',
        iter(float(i) for i in range(benchmark.REQUEST_COUNT * 2)).__next__
    )

    request_times, downloaded_sizes, total_bytes = benchmark.run_benchmark(
        'https://example.com/file'
    )

    assert len(request_times) == 10
    assert request_times == [1.0] * 10

    assert downloaded_sizes == [6] * 10
    assert total_bytes == 60

    assert len(opened_responses) == 10
    assert all(response.closed for response in responses)

    for response in responses:
        assert response.read_calls == [
            benchmark.CHUNK_SIZE,
            benchmark.CHUNK_SIZE,
            benchmark.CHUNK_SIZE,
        ]


def test_run_benchmark_handles_http_error(monkeypatch):
    """
    Проверяет завершение программы с кодом 1 при HTTP-ошибке.
    """

    monkeypatch.setattr(
        benchmark,
        'urlopen',
        lambda *args, **kwargs: (_ for _ in ()).throw(
            HTTPError(
                'https://example.com/file',
                404,
                'Not Found',
                None,
                None,
            )
        )
    )

    monkeypatch.setattr(benchmark, 'finish_progress', lambda: None)

    with pytest.raises(SystemExit) as error:
        benchmark.run_benchmark('https://example.com/file')

    assert error.value.code == 1


def test_run_benchmark_handles_url_error(monkeypatch):
    """Проверяем обработку ошибки URL или соединения."""

    monkeypatch.setattr(
        benchmark,
        'urlopen',
        lambda *args, **kwargs: (_ for _ in ()).throw(
            URLError('Connection failed')
        )
    )

    monkeypatch.setattr(benchmark, 'finish_progress', lambda: None)

    with pytest.raises(SystemExit) as error:
        benchmark.run_benchmark('https://example.com/file')

    assert error.value.code == 1


def test_run_benchmark_handles_os_error(monkeypatch):
    """Проверяем обработку системной ошибки, например тайм-аута."""

    monkeypatch.setattr(
        benchmark,
        'urlopen',
        lambda *args, **kwargs: (_ for _ in ()).throw(
            OSError('Connection timed out')
        )
    )

    monkeypatch.setattr(benchmark, 'finish_progress', lambda: None)

    with pytest.raises(SystemExit) as error:
        benchmark.run_benchmark('https://example.com/file')

    assert error.value.code == 1


def test_calculate_results():
    """
    Проверяет корректность расчёта статистических показателей
    и средней скорости загрузки.
    """

    request_times = [1.0, 2.0, 3.0]
    total_bytes = 3_000_000

    results = benchmark.calculate_results(request_times, total_bytes)

    assert results['average_time'] == 2.0
    assert results['median_time'] == 2.0
    assert results['total_time'] == 6.0
    assert results['total_bytes'] == 3_000_000
    assert results['total_mb'] == 3.0
    assert results['speed_mbps'] == pytest.approx(4.0)


@pytest.mark.parametrize(
    'request_times, downloaded_sizes, total_bytes',
    [
        ([], [], 0),
        ([1.0], [], 1),
        ([1.0], [0], 0),
        ([0.0], [1], 1),
    ]
)
def test_validate_results_rejects_invalid_data(
        request_times,
        downloaded_sizes,
        total_bytes,
):
    """
    Проверяет, что валидация отклоняет некорректные результаты.

    Проверяются отсутствие запросов, несоответствие количества
    результатов, отсутствие загруженных данных и нулевое время.
    """

    with pytest.raises(SystemExit) as error:
        benchmark.validate_results(
            request_times,
            downloaded_sizes,
            total_bytes,
        )

    assert error.value.code == 1


def test_validate_results_accepts_valid_data():
    """
    Проверяет успешную валидацию корректных результатов тестирования.
    """

    benchmark.validate_results(
        request_times=[1.0, 2.0],
        downloaded_sizes=[100, 200],
        total_bytes=300,
    )
