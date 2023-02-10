from PyQt5 import uic
from PyQt5.QtWidgets import *

from dft_model import Dft_model
from stft_model import Stft_model
from rt_sine_transformation import Rt_sine_transformation


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('main.ui', self)

        self.page1_btn.clicked.connect(self.go_to_first)
        self.page2_btn.clicked.connect(self.go_to_second)
        self.page3_btn.clicked.connect(self.go_to_third)

        # First page
        self.dft_tab = Dft_model()
        self.stackedWidget.addWidget(self.dft_tab)  # Add page to the stacked widget

        # Second page
        self.stft_tab = Stft_model()
        self.stackedWidget.addWidget(self.stft_tab)  # Add page to the stacked widget

        # Third page
        self.rt_sine_trans_tab = Rt_sine_transformation()
        self.stackedWidget.addWidget(self.rt_sine_trans_tab)

    def go_to_first(self):
        self.stackedWidget.setCurrentIndex(0)
        self.rt_sine_trans_tab.listening = False

    def go_to_second(self):
        self.stackedWidget.setCurrentIndex(1)
        self.rt_sine_trans_tab.listening = False

    def go_to_third(self):
        self.stackedWidget.setCurrentIndex(2)
        self.rt_sine_trans_tab.listening = True


if __name__ == '__main__':
    app = QApplication([])
    window = MainWindow()
    window.show()
    window.rt_sine_trans_tab.animation()
    window.rt_sine_trans_tab.saveResult()
    app.exec_()
