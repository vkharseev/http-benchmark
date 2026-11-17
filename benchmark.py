import statistics  # Модуль для математической статистики. Расчёт среднего значения
import time  # Модуль для работы со временем. Измерение времени
from urllib.error import HTTPError, URLError  # Обработка HTTP-ошибок
from urllib.request import urlopen  # Выполнение HTTP-запросов

from custom_argument_parser import CustomArgumentParser  # Модуль для обработки аргументов командной строки
from progress_bar import print_progress, finish_progress  # Модуль прогресс-бара

APP_NAME = 'Тестирование скорости загрузки по протоколу HTTP'  # название приложения
REQUEST_COUNT = 10  # Количество запросов.
CHUNK_SIZE = 64 * 1024  # Размер блока, которым будем читать ответ сервера (64 килобайта)
TIMEOUT = 30  # Максимальное время ожидания ответа от сервера (30 секунд)


def run_benchmark(url: str) -> tuple[list[float], list[int], int]:
    request_times = []  # содержит список продолжительностей каждого запроса
    total_bytes = 0  # общее количество скачанных байтов
    downloaded_sizes = []  # список размеров каждого ответа
    try:
        for request_number in range(1, REQUEST_COUNT + 1):
            start_time = time.perf_counter()  # показание высокоточного таймера на момент начала запроса
            downloaded_bytes = 0  # количество загруженных байтов

            with urlopen(url, timeout=TIMEOUT) as response:
                while True:
                    chunk = response.read(CHUNK_SIZE)

                    if not chunk:
                        break

                    downloaded_bytes += len(chunk)

            end_time = time.perf_counter()  # показание высокоточного таймера на момент завершения запроса
            request_time = end_time - start_time
            request_times.append(request_time)
            downloaded_sizes.append(downloaded_bytes)
            total_bytes += downloaded_bytes

            print_progress(request_number, REQUEST_COUNT)

    except HTTPError as error:  # обработка HTTP-ошибок, например 404 или 500.
        print(f'HTTP error: {error.code} - {error.reason}')
        raise SystemExit(1)

    except URLError as error:  # обработка ошибок URL и сетевого соединения
        print(f'URL error: {error.reason}')
        raise SystemExit(1)

    except OSError as error:  # обработка ошибки Timeout
        print(f'Connection error: {error}')
        raise SystemExit(1)

    finally:
        finish_progress()

    return request_times, downloaded_sizes, total_bytes


def calculate_results(request_times: list[float], total_bytes: int) -> dict[str, float | int]:
    average_time = statistics.mean(request_times)  # расчёт среднего арифметического значений списка
    median_time = statistics.median(request_times)  # расчёт медианного значений списка
    total_time = sum(request_times)  # Общее время выполнения HTTP-запросов
    total_mb = total_bytes / 1_000_000  # Общий объем скачанных данных в Мб
    speed_mbps = ((total_bytes * 8) / total_time) / 1_000_000 if total_time > 0 else 0

    return {
        'average_time': average_time,
        'median_time': median_time,
        'total_time': total_time,
        'total_bytes': total_bytes,
        'total_mb': total_mb,
        'speed_mbps': speed_mbps,
    }


def validate_results(request_times: list[float], downloaded_sizes: list[int], total_bytes: int) -> None:
    if not request_times:
        print('Ошибка: Отсутствуют успешные запросы')
        raise SystemExit(1)

    if len(request_times) != len(downloaded_sizes):
        print('Ошибка: Количество запросов не совпадает с количеством ответов')
        raise SystemExit(1)

    if total_bytes == 0:
        print('Ошибка: Данные не загружены')
        raise SystemExit(1)

    if sum(request_times) <= 0:
        print('Ошибка: Общее время запросов должно быть больше нуля')
        raise SystemExit(1)


def print_results(results: dict[str, float | int], downloaded_sizes: list[int], request_times: list[float]) -> None:
    print('\nДетали запросов:')
    print('-' * 40)

    for request_number, (request_time, downloaded_bytes) in enumerate(
            zip(request_times, downloaded_sizes),
            start=1
    ):
        print(
            f'Запрос {request_number}: '
            f'{request_time:.3f} сек, '
            f'{downloaded_bytes / 1_000_000:.2f} MB'
        )

    print('\nИтого:')
    print('-' * 40)

    print(f'Среднее время выполнения запроса: {results["average_time"]:.3f} сек')
    print(f'Медианное время выполнения запроса: {results["median_time"]:.3f} сек')
    print(f'Всего скачано: {results["total_mb"]:.2f} MB')
    print(f'Общее время: {results["total_time"]:.3f} сек')
    print(f'Средняя скорость загрузки: {results["speed_mbps"]:.2f} Mbps')


def main() -> None:
    parser = CustomArgumentParser(
        description=APP_NAME,
        usage='%(prog)s <URL>'
    )

    parser.add_argument(
        'url',
        help='URL для скачивания'
    )
    print(f'\n{APP_NAME}\n')
    args = parser.parse_args()
    request_times, downloaded_sizes, total_bytes = run_benchmark(args.url)
    validate_results(request_times, downloaded_sizes, total_bytes)
    results = calculate_results(request_times, total_bytes)
    print_results(results, downloaded_sizes, request_times)


if __name__ == "__main__":
    main()
