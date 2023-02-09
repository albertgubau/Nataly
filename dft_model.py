from PyQt5 import uic
from PyQt5.QtWidgets import *


class Dft_model(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi('dft_model.ui', self)

        self.browse_button = self.findChild(QPushButton, "browse_btn")
        self.input_text_box = self.findChild(QLineEdit, "filename")
        self.browse_button.clicked.connect(lambda: self.browse_file())

    def browse_file(self):
        # Open File Dialog (returns a tuple)
        fname = QFileDialog.getOpenFileName(self, "Open File", "", "All Files (*)")

        # Output filename to screen
        if fname:
            self.input_text_box.setText(str(fname[0]))  # We should modifiy the input text box
            # print(self.input_text_box.text()) # Get the text from the text box (i.e, path to the input file)