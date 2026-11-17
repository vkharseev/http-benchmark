def print_progress(current, total):
    progress = current / total

    progress_bar = (
            '█' * current +
            '░' * (total - current)
    )

    print(
        f'\r{current}/{total}: '
        f'[{progress_bar}] {progress:.0%}',
        end='',
        flush=True
    )


def finish_progress():
    print(end='\n')
