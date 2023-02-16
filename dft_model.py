from PyQt5 import uic
from PyQt5.QtWidgets import *

import numpy as np
from scipy import signal
import matplotlib.pyplot as plt
import essentia.standard as es
import struct
import pyaudio
import sounddevice as sd

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
from PyQt5.QtCore import *


fs = 44100

# Instantiate the Essentia Algorithms
w = es.Windowing(type='hamming', size=2048)
spectrum = es.Spectrum()
fft = es.FFT(size=2048)
sineAnal = es.SineModelAnal(sampleRate=fs,
                            maxnSines=150,
                            magnitudeThreshold=-120,
                            freqDevOffset=10,
                            freqDevSlope=0.001)

sineSynth = es.SineModelSynth(sampleRate=fs, fftSize=2048, hopSize=512)
ifft = es.IFFT(size=2048)
overl = es.OverlapAdd(frameSize=2048, hopSize=512)
awrite = es.MonoWriter(filename='output.wav', sampleRate=fs)
awrite2 = es.MonoWriter(filename='prova.wav', sampleRate=fs)


class Dft_model(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi('dft_model.ui', self)

        self.browse_button = self.findChild(QPushButton, "browse_btn")
        self.input_text_box = self.findChild(QLineEdit, "filename")
        self.browse_button.clicked.connect(lambda: self.browse_file())

        pg.setConfigOptions(antialias=True)
        self.win = pg.GraphicsLayoutWidget(self)
        self.win.setGeometry(QRect(20, 160, 681, 141))
        self.win.setBackground('w')

        self.win2 = pg.GraphicsLayoutWidget(self)
        self.win2.setGeometry(QRect(20, 330, 681, 201))
        self.win2.setBackground('w')

        # Interpret image data as row-major instead of col-major
        pg.setConfigOptions(imageAxisOrder='row-major')


        # Add plots to the window
        self.waveform = self.win.addPlot(
            title='WAVEFORM', row=1, col=1
        )

        # Add plots to the window
        self.spectrogram = self.win2.addPlot(
            title='SPECTROGRAM', row=1, col=1
        )

        # Item for displaying image data
        self.img = pg.ImageItem()
        self.spectrogram.addItem(self.img)

        # Add a histogram with which to control the gradient of the image
        self.hist = pg.HistogramLUTItem()
        # Link the histogram to the image
        self.hist.setImageItem(self.img)
        # If you don't add the histogram to the window, it stays invisible, but I find it useful.
        self.win2.addItem(self.hist, row=1, col=2)

        # Custom ROI for selecting an image region
        self.roi = pg.ROI([-8, 14], [6, 5], pen='r')
        self.roi.addScaleHandle([0.5, 1], [0.5, 0.5])
        self.roi.addScaleHandle([0, 0.5], [0.5, 0.5])
        self.spectrogram.addItem(self.roi)
        self.roi.setZValue(10)  # make sure ROI is drawn above image
        self.roi.sigRegionChanged.connect(lambda: self.SelectedRegion())



        self.x = None

    def browse_file(self):
        # Open File Dialog (returns a tuple)
        fname = QFileDialog.getOpenFileName(self, "Open File", "", "All Files (*)")

        # Output filename to screen
        if fname:
            self.input_text_box.setText(str(fname[0]))  # We should modifiy the input text box
            self.x = es.MonoLoader(filename=self.input_text_box.text())()
            # print(self.input_text_box.text()) # Get the text from the text box (i.e, path to the input file)
            self.waveform.clear()
            self.img.clear()
            self.waveform.plot(self.x, pen='g')

            spec = np.array([])

            frames = 0
            for frame in es.FrameGenerator(audio=self.x, frameSize=2048, hopSize=512):
                frame_spectrum = spectrum(w(frame))

                if frames == 0:  # First frame
                    spec = frame_spectrum

                else:  # Next frames
                    spec = np.vstack((spec, frame_spectrum))

                frames+=1

            #self.spectrogram.plot(np.transpose(spec), pen='g')


            # Fit the min and max levels of the histogram to the data available
            self.hist.setLevels(np.min(spec), np.max(spec))
            # This gradient is roughly comparable to the gradient used by Matplotlib
            # You can adjust it and then save it using hist.gradient.saveState()
            self.hist.gradient.restoreState(
                {'mode': 'rgb',
                 'ticks': [(0.5, (0, 182, 188, 255)),
                           (1.0, (246, 111, 0, 255)),
                           (0.0, (75, 0, 113, 255))]})

            print(np.transpose(spec))
            self.img.setImage(np.transpose(spec))
            print(self.img.image)

    def SelectedRegion(self):
        selected = self.roi.getArrayRegion(self.img.image,self.img)
        print(selected[:,0].size)
