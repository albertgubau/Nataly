from PyQt5 import uic
from PyQt5.QtWidgets import *


class Stft_model(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi('new_page.ui', self)
