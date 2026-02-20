import ttkbootstrap as tb
from ui.main_window import MainWindow
from db.db import Database


def main():
    db = Database('data.db')
    app = MainWindow(db)
    app.run()


if __name__ == '__main__':
    main()
