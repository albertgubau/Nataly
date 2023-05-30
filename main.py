from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow, QApplication, QLabel, QPushButton
from PyQt5.QtGui import QPixmap

from GUIs.sinusoidal_spec_synth import Sinusoidal_Spec_Synth
from GUIs.rt_sine_transformation import Rt_sine_transformation


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Load the ui file
        uic.loadUi('main.ui', self)

        # Initially we will always be on dark mode (I like it)
        self.dark_mode = True

        # Get the widgets of the interface and connect them with their callbacks
        self.essentia_logo = self.findChild(QLabel, "essentia_logo")
        self.nataly_logo = self.findChild(QLabel, "nataly_logo")

        self.page1_btn.clicked.connect(self.go_to_first)
        self.page1_btn.setStyleSheet('border:3px solid gray;')
        self.page2_btn.clicked.connect(self.go_to_second)

        # First page
        self.sinusoidal_spec_anal_tab = Sinusoidal_Spec_Synth()
        self.stackedWidget.addWidget(self.sinusoidal_spec_anal_tab)  # Add page to the stacked widget

        # Third page
        self.rt_sine_trans_tab = Rt_sine_transformation()
        self.stackedWidget.addWidget(self.rt_sine_trans_tab)

        # Change theme button
        self.change_theme_btn = self.findChild(QPushButton, "change_theme_btn")
        self.change_theme_btn.clicked.connect(lambda: self.change_theme())
        self.change_theme_btn.setText('\u263C')

    # Method to go to the first page (Spectrogram Sound Analyzer)
    def go_to_first(self):
        self.page2_btn.setStyleSheet('')
        self.page1_btn.setStyleSheet('border:3px solid gray;')
        self.stackedWidget.setCurrentIndex(0)
        self.rt_sine_trans_tab.listening = False

    # Method to go to the second page (Real-Time Sinusoidal Transformation)
    def go_to_second(self):
        self.page1_btn.setStyleSheet('')
        self.page2_btn.setStyleSheet('border:3px solid gray;')
        self.stackedWidget.setCurrentIndex(1)
        self.rt_sine_trans_tab.listening = True

    # Method in charge of changing the stylesheet of the window to change the theme of the application
    def change_theme(self):

        if self.dark_mode:
            # Change the main window theme colors
            self.setStyleSheet(''
                               'QLabel{'
                               'color:black;'
                               '}'
                               'QPushButton{'
                               'background-color: #0096FF;border-radius: 10px;color: white;'
                               '}'
                               'QPushButton:hover{'
                               'background-color: #3063A5;'
                               '}'
                               'QMainWindow{'
                               'background-color:#dbdbdb '
                               '};')

            self.essentia_logo.setPixmap(QPixmap('./assets/essentia_logo_light.png'))

            self.nataly_logo.setPixmap(QPixmap('./assets/nataly_logo_light.png'))

            self.stackedWidget.setStyleSheet(''
                                             'QStackedWidget{'
                                             'background-color:#eaebeb;'
                                             'border-radius:10px'
                                             '}'
                                             'QPushButton {'
                                             'background-color: #0096FF;'
                                             'border-radius: 10px;'
                                             'color: white;'
                                             '}'
                                             'QPushButton:!enabled{'
                                             'background-color: rgb(119, 118, 123);'
                                             'color: rgb(154, 153, 150);'
                                             '}'
                                             'QPushButton:hover {'
                                             'background-color: #3063A5;'
                                             '}'
                                             'QCheckBox {'
                                             'color:black;'
                                             '}'
                                             'QCheckBox::indicator { '
                                             'border: 1px solid black;'
                                             'border-radius:7px;'
                                             '}'
                                             'QCheckBox::indicator:checked {'
                                             'background-color:#0096FF;'
                                             '}'
                                             'QSlider {'
                                             'background-color: white;'
                                             'color: white;'
                                             'border : 0.1em;'
                                             'height:  1.5em;'
                                             'border-radius:7px;'
                                             '}'
                                             'QSlider:hover {'
                                             'background-color:#dbdbdb'
                                             '};')

            self.sinusoidal_spec_anal_tab.dark_mode = False
            self.sinusoidal_spec_anal_tab.change_theme()

            self.rt_sine_trans_tab.dark_mode = False
            self.rt_sine_trans_tab.change_theme()
            self.change_theme_btn.setText(' \u263E')

        else:
            # Change the main window theme colors
            self.setStyleSheet(''
                               'QLabel{'
                               'color:white;'
                               '}'
                               'QPushButton {'
                               'background-color: #0096FF;border-radius: 10px;color: white;'
                               '}'
                               'QPushButton:hover {'
                               'background-color: #3063A5;'
                               '}'
                               'QMainWindow{'
                               'background-color:#1f1f1f '
                               '};')

            self.essentia_logo.setPixmap(QPixmap('./assets/essentia_logo.svg'))

            self.nataly_logo.setPixmap(QPixmap('./assets/nataly_logo.png'))

            self.stackedWidget.setStyleSheet(''
                                             'QStackedWidget{'
                                             'background-color:#2e2e2e;'
                                             'border-radius:10px'
                                             '}'
                                             'QPushButton {'
                                             'background-color: #0096FF;'
                                             'border-radius: 10px;'
                                             'color: white;'
                                             '}'
                                             'QPushButton:!enabled{'
                                             'background-color: rgb(119, 118, 123);'
                                             'color: rgb(154, 153, 150);'
                                             '}'
                                             'QPushButton:hover {'
                                             'background-color: #3063A5;'
                                             '}'
                                             'QCheckBox {'
                                             'color:white;'
                                             '}'
                                             'QCheckBox::indicator { '
                                             'border: 1px solid white;'
                                             'border-radius:7px;'
                                             '}'
                                             'QCheckBox::indicator:checked {'
                                             'background-color:#0096FF;'
                                             '}'
                                             'QSlider {'
                                             'background-color: #FF3B3B3B;'
                                             'color: white;'
                                             'border : 0.1em;'
                                             'height:  1.5em;'
                                             'border-radius:7px;'
                                             '}'
                                             'QSlider:hover {'
                                             'background-color:rgb(94, 92, 100)'
                                             '};')

            self.sinusoidal_spec_anal_tab.dark_mode = True
            self.sinusoidal_spec_anal_tab.change_theme()

            self.rt_sine_trans_tab.dark_mode = True
            self.rt_sine_trans_tab.change_theme()
            self.change_theme_btn.setText('\u263C')

        self.dark_mode = not self.dark_mode

# Executing loop
if __name__ == '__main__':
    app = QApplication([])
    window = MainWindow()
    window.show()
    window.rt_sine_trans_tab.animation()
    app.exec_()
    exit()
