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
awrite = es.MonoWriter(filename='output_synthesis.wav', sampleRate=fs)


class Dft_model(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        uic.loadUi('dft_model.ui', self)

        self.browse_button = self.findChild(QPushButton, "browse_btn")
        self.input_text_box = self.findChild(QLineEdit, "filename")
        self.browse_button.clicked.connect(lambda: self.browse_file())

        self.compute_button = self.findChild(QPushButton, "compute_btn")
        self.compute_button.clicked.connect(lambda: self.plot())

        pg.setConfigOptions(antialias=True)
        # self.win = pg.GraphicsLayoutWidget(self)
        # self.win.setGeometry(QRect(20, 160, 681, 141))
        # self.win.setBackground('w')

        self.win2 = pg.GraphicsLayoutWidget(self)
        self.win2.setGeometry(QRect(20, 160, 721, 371))
        self.win2.setBackground('w')

        # Interpret image data as row-major instead of col-major
        pg.setConfigOptions(imageAxisOrder='row-major')

        # Add plots to the window
        # self.waveform = self.win.addPlot(
        #    title='WAVEFORM', row=1, col=1
        # )

        # Add plots to the window
        self.spectrogram = self.win2.addPlot(
            title='SPECTROGRAM', row=1, col=1
        )
        # Add plots to the window
        self.region = self.win2.addPlot(
            title='REGION', row=2, col=1
        )

        # Item for displaying image data
        self.img = pg.ImageItem()
        self.spectrogram.addItem(self.img)

        self.img2 = pg.ImageItem()
        self.region.addItem(self.img2)

        # Add a histogram with which to control the gradient of the image
        self.hist = pg.HistogramLUTItem()
        # Link the histogram to the image
        self.hist.setImageItem(self.img)
        # If you don't add the histogram to the window, it stays invisible, but I find it useful.
        self.win2.addItem(self.hist, row=1, col=2)

        # Custom ROI for selecting an image region
        self.roi = pg.ROI([-8, 14], [6, 5], pen='r', handlePen='g', handleHoverPen='b')
        self.roi.addScaleHandle([1, 1], [0, 0])
        self.roi.addScaleHandle([0, 0], [1, 1])
        self.roi.addScaleHandle([0, 1], [1, 0])
        self.roi.addScaleHandle([1, 0], [0, 1])
        self.spectrogram.addItem(self.roi)
        self.roi.setZValue(10)  # make sure ROI is drawn above image
        self.roi.sigRegionChanged.connect(lambda: self.SelectedRegion())

        self.x = None
        self.spec = None
        self.sinusoids = None

    def browse_file(self):
        # Open File Dialog (returns a tuple)
        fname = QFileDialog.getOpenFileName(self, "Open File", "", "All Files (*)")

        # Output filename to screen
        if fname:
            self.input_text_box.setText(str(fname[0]))  # We should modifiy the input text box
            self.x = es.MonoLoader(filename=self.input_text_box.text())()

            # self.waveform.clear()
            self.img.clear()
            self.img2.clear()
            # self.waveform.plot(self.x, pen='g')

            self.spec = np.array([])
            self.sinusoids = np.array([])

            frames = 0
            for frame in es.FrameGenerator(audio=self.x, frameSize=2048, hopSize=512):

                frame_spectrum = spectrum(w(frame))

                infft = fft(w(frame))

                sine_anal = sineAnal(infft)

                if frames == 0:  # First frame
                    self.spec = frame_spectrum
                    self.sinusoids = sine_anal[0]
                    self.magnitudes = sine_anal[1]
                    self.phases = sine_anal[2]

                else:  # Next frames
                    self.spec = np.vstack((self.spec, frame_spectrum))
                    self.sinusoids = np.vstack((self.sinusoids, sine_anal[0]))
                    self.magnitudes = np.vstack((self.magnitudes, sine_anal[1]))
                    self.phases = np.vstack((self.phases, sine_anal[1]))

                frames += 1

            # Fit the min and max levels of the histogram to the data available
            self.hist.setLevels(np.min(self.spec), np.max(self.spec))
            # This gradient is roughly comparable to the gradient used by Matplotlib
            # You can adjust it and then save it using hist.gradient.saveState()
            self.hist.gradient.restoreState(
                {'mode': 'rgb',
                 'ticks': [(0.5, (0, 182, 188, 255)),
                           (1.0, (246, 111, 0, 255)),
                           (0.0, (75, 0, 113, 255))]})

            self.img.setImage(np.transpose(self.spec))
            self.spectrogram.setYRange(0, 1000)
            self.spectrogram.setXRange(0, np.transpose(self.spec)[0, :].size)

    def SelectedRegion(self):

        self.selected, self.indexes = self.roi.getArrayRegion(self.img.image, self.img, returnMappedCoords=True)

        self.img2.clear()
        self.img2.setImage(self.selected)

        self.frames_start = int(self.indexes[1][0][0])
        self.frames_end = int(self.indexes[1][-1][-1])

        print(self.frames_start)
        if(self.frames_start<=0):
            self.frames_start = 0

        self.bins_start = int(self.indexes[0][0][0])
        self.bins_end = int(self.indexes[0][-1][0])

        self.frequencies_start = (self.bins_start*fs)/2048 # Convert it to frequency values
        self.frequencies_end = (self.bins_end*fs)/2048  # Convert it to frequency values

        self.synthesis()

    def synthesis(self):

        self.spec2 = np.copy(self.spec)

        ## Spectrogram synthesis (gives 0 values for non-selected regions of the spectrogram)
        #for f in range(0, len(self.spec2)): # For every frame
        #    for i in range(0, len(self.spec2[0])): # For every bin of the frame
        #        if (f <= self.frames_start or f >= self.frames_end) or (i <= self.bins_start or i >= self.bins_end):
        #            self.spec2[f][i] = 0.0
        
        print(np.transpose(self.spec2))

        self.sinusoids2 = np.copy(self.sinusoids)
        self.magnitudes2 = np.copy(self.magnitudes)
        self.phases2 = np.copy(self.phases)

        # Sinusoids synthesis (gives 0 values for non-selected regions of the sinusoids)
        for f in range(0, len(self.sinusoids2)): # For every frame
            for i in range(0, len(self.sinusoids2[0])): # For every bin of the frame
                if (self.sinusoids2[f][i] <= self.frequencies_start or self.sinusoids2[f][i]>=self.frequencies_end) or (f <= self.frames_start or f >= self.frames_end):
                    self.sinusoids2[f][i] = 0.0
                    self.magnitudes2[f][i] = 0.0
                    self.phases2[f][i] = 0.0

    def plot(self):

        y = np.array([])  # initialize output array

        frames = 0

        for frame in es.FrameGenerator(audio=self.x, frameSize=2048, hopSize=512):

            # Synthesis (with OverlapAdd and IFFT)
            fft_synth = sineSynth(self.magnitudes2[frames], self.sinusoids2[frames], self.phases2[frames])

            out = overl(ifft(fft_synth))

            # Save result
            y = np.append(y, out)

            frames += 1

        # Write the output file to the specified location
        awrite(y)

        plt.figure()
        plt.subplot(2,1,1)
        # Plotting with Matplotlib in comparison
        plt.pcolormesh(np.transpose(self.spec2))
        plt.colorbar()


        # This plot is not correct I think, maybe for the result of applying the essentia function
        plt.subplot(2, 1, 2)
        if (self.sinusoids2.shape[1] > 0):
            numFrames = self.sinusoids2.shape[0]
            frmTime = 512 * np.arange(numFrames) / float(fs)
            self.sinusoids2[self.sinusoids2 <= 0] = np.nan
            plt.plot(self.sinusoids2)
            plt.axis([0, 187, 0, 22000])
            plt.title('frequencies of sinusoidal tracks')

        plt.show()