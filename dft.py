# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'dft_model.ui'
#
# Created by: PyQt5 UI code generator 5.15.7
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(761, 541)
        self.title_label = QtWidgets.QLabel(Form)
        self.title_label.setGeometry(QtCore.QRect(20, 10, 301, 91))
        font = QtGui.QFont()
        font.setFamily("Sans")
        font.setPointSize(35)
        font.setBold(True)
        font.setWeight(75)
        self.title_label.setFont(font)
        self.title_label.setObjectName("title_label")
        self.filename = QtWidgets.QLineEdit(Form)
        self.filename.setGeometry(QtCore.QRect(100, 110, 321, 21))
        self.filename.setObjectName("filename")
        self.input_label = QtWidgets.QLabel(Form)
        self.input_label.setGeometry(QtCore.QRect(20, 110, 91, 21))
        self.input_label.setObjectName("input_label")
        self.browse_btn = QtWidgets.QPushButton(Form)
        self.browse_btn.setGeometry(QtCore.QRect(440, 110, 89, 21))
        self.browse_btn.setObjectName("browse_btn")

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.title_label.setText(_translate("Form", "DFT Model"))
        self.input_label.setText(_translate("Form", "Input File:"))
        self.browse_btn.setText(_translate("Form", "Browse"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Form = QtWidgets.QWidget()
    ui = Ui_Form()
    ui.setupUi(Form)
    Form.show()
    sys.exit(app.exec_())
