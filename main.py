import os
import sys

from PyQt5 import uic
from PyQt5.QtWidgets import *

from sinusoidal_spec_anal import Sinusoidal_Spec_Anal
from stft_model import Stft_model
from rt_sine_transformation import Rt_sine_transformation


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('main.ui', self)

        self.page1_btn.clicked.connect(self.go_to_first)
        self.page3_btn.clicked.connect(self.go_to_second)

        # First page
        self.sinusoidal_spec_anal_tab = Sinusoidal_Spec_Anal()
        self.stackedWidget.addWidget(self.sinusoidal_spec_anal_tab)  # Add page to the stacked widget

        # Third page
        self.rt_sine_trans_tab = Rt_sine_transformation()
        self.stackedWidget.addWidget(self.rt_sine_trans_tab)

    def go_to_first(self):
        self.stackedWidget.setCurrentIndex(0)
        self.rt_sine_trans_tab.listening = False

    def go_to_second(self):
        self.stackedWidget.setCurrentIndex(1)
        self.rt_sine_trans_tab.listening = True


if __name__ == '__main__':
    app = QApplication([])
    window = MainWindow()
    window.show()
    window.rt_sine_trans_tab.animation()
    app.exec_()
    exit()

