import argparse


class CustomArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage()
        self.exit(2, 'Ошибка: укажите URL для загрузки.\n')
