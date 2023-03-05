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
N = 2048
H = N // 4

# Instantiate the Essentia Algorithms
w = es.Windowing(type='hamming', size=2000)
spectrum = es.Spectrum()
fft = es.FFT(size=N)
sineAnal = es.SineModelAnal(sampleRate=fs,
                            maxnSines=150,
                            magnitudeThreshold=-80,
                            freqDevOffset=10,
                            freqDevSlope=0.001)

sineSynth = es.SineModelSynth(sampleRate=fs, fftSize=N, hopSize=H)
ifft = es.IFFT(size=N)
overl = es.OverlapAdd(frameSize=N, hopSize=H)
awrite = es.MonoWriter(filename='output_synthesis.wav', sampleRate=fs)


class Sinusoidal_Spec_Anal(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        uic.loadUi('sinusoidal_spec_anal.ui', self)

        self.browse_button = self.findChild(QPushButton, "browse_btn")
        self.input_text_box = self.findChild(QLineEdit, "filename")
        self.browse_button.clicked.connect(lambda: self.browse_file())

        self.compute_button = self.findChild(QPushButton, "compute_btn")
        self.compute_button.clicked.connect(lambda: self.plot())

        self.play_button = self.findChild(QPushButton, "play_btn")
        self.play_button.clicked.connect(lambda: self.play_result())

        self.pause_button = self.findChild(QPushButton, "pause_btn")
        self.pause_button.clicked.connect(lambda: self.stop_result())

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

        sp_xaxis = pg.AxisItem(orientation='bottom')
        sp_xaxis.setScale(scale=H / fs)
        sp_yaxis = pg.AxisItem(orientation='left')
        sp_yaxis.setScale(scale=fs / N)

        # Add plots to the window
        self.spectrogram = self.win2.addPlot(
            title='SPECTROGRAM', row=1, col=1, axisItems={'bottom': sp_xaxis, 'left': sp_yaxis}
        )

        self.spectrogram.setLabel('bottom', "Time (s)")
        self.spectrogram.setLabel('left', "Frequency (Hz)")

        # Add plots to the window
        # self.region = self.win2.addPlot(
        #    title='REGION', row=2, col=1
        # )

        # Item for displaying image data
        self.img = pg.ImageItem()
        self.spectrogram.addItem(self.img)

        # self.img2 = pg.ImageItem()
        # self.region.addItem(self.img2)

        # Add a histogram with which to control the gradient of the image
        self.hist = pg.HistogramLUTItem()
        # Link the histogram to the image
        self.hist.setImageItem(self.img)
        # If you don't add the histogram to the window, it stays invisible, but I find it useful.
        self.win2.addItem(self.hist, row=1, col=2)

        # Custom ROI for selecting an image region
        self.roi = pg.ROI([50, 50], [100, 200], pen='r', handlePen='g', handleHoverPen='b')
        self.roi.addScaleHandle([1, 1], [0, 0])
        self.roi.addScaleHandle([0, 0], [1, 1])
        self.roi.addScaleHandle([0, 1], [1, 0])
        self.roi.addScaleHandle([1, 0], [0, 1])
        self.spectrogram.addItem(self.roi)
        self.roi.setZValue(10)  # make sure ROI is drawn above image
        self.roi.sigRegionChangeFinished.connect(lambda: self.SelectedRegion())
        self.roi.sigRegionChanged.connect(lambda: self.movedRegion())

        self.y = None
        self.x = None
        self.spec = None
        self.sinusoids = None
        self.phases2 = None
        self.magnitudes2 = None
        self.sinusoids2 = None
        self.spec2 = None
        self.frequencies_start = None
        self.frequencies_end = None
        self.bins_start = None
        self.bins_end = None
        self.frames_start = None
        self.frames_end = None
        self.phases = None
        self.magnitudes = None
        self.indexes = None
        self.selected = None

    def browse_file(self):
        # Open File Dialog (returns a tuple)
        fname = QFileDialog.getOpenFileName(self, "Open File", "", "All Files (*)")

        # Output filename to screen
        if fname:
            self.input_text_box.setText(str(fname[0]))  # We should modifiy the input text box
            self.x = es.MonoLoader(filename=self.input_text_box.text())()

            # self.waveform.clear()
            self.img.clear()
            # self.img2.clear()
            # self.waveform.plot(self.x, pen='g')

            self.spec = np.array([])
            self.sinusoids = np.array([])

            frames = 0
            for frame in es.FrameGenerator(audio=self.x, frameSize=N, hopSize=H, startFromZero=True):

                frame_spectrum = spectrum(w(frame))

                infft = fft(w(frame))

                sine_anal = sineAnal(infft)

                if frames == 0:  # First frame
                    self.spec = frame_spectrum
                    self.sinusoids = np.array([sine_anal[0]])
                    self.magnitudes = np.array([sine_anal[1]])
                    self.phases = np.array([sine_anal[2]])

                else:  # Next frames
                    self.spec = np.vstack((self.spec, frame_spectrum))
                    self.sinusoids = np.vstack((self.sinusoids, np.array([sine_anal[0]])))
                    self.magnitudes = np.vstack((self.magnitudes, np.array([sine_anal[1]])))
                    self.phases = np.vstack((self.phases, np.array([sine_anal[2]])))

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
            
            spectrogram = np.transpose(self.spec)

            self.img.setImage(spectrogram)
            # set up the correct scaling for y-axis

            self.spectrogram.setYRange(0, 300)
            self.spectrogram.setXRange(0, np.transpose(self.spec)[0, :].size)
            self.roi.setPos(0, 0)

    def movedRegion(self):

        self.selected = self.roi.getArrayRegion(self.img.image, self.img)

        # self.img2.clear()
        # self.img2.setImage(self.selected)

    def SelectedRegion(self):

        self.selected, self.indexes = self.roi.getArrayRegion(self.img.image, self.img, returnMappedCoords=True)

        self.frames_start = int(self.indexes[1][0][0])
        self.frames_end = int(self.indexes[1][-1][-1])

        print(self.frames_start)
        print(self.frames_end)

        if self.frames_start <= 0:
            self.frames_start = 0

        numFrames = np.transpose(self.spec)[0, :].size

        if self.frames_end >= numFrames:
            self.frames_end = numFrames

        self.bins_start = int(self.indexes[0][0][0])
        self.bins_end = int(self.indexes[0][-1][0])

        if self.bins_start <= 0:
            self.bins_start = 0

        numFreqs = np.transpose(self.spec)[:, 0].size

        if self.bins_end >= numFreqs:
            self.bins_end = numFreqs

        print(self.bins_start)
        print(self.bins_end)

        self.frequencies_start = (self.bins_start * fs) / N  # Convert it to frequency values
        self.frequencies_end = (self.bins_end * fs) / N  # Convert it to frequency values

        self.synthesis()

    def synthesis(self):

        self.sinusoids2 = np.copy(self.sinusoids[self.frames_start:self.frames_end])
        self.magnitudes2 = np.copy(self.magnitudes[self.frames_start:self.frames_end])
        self.phases2 = np.copy(self.phases[self.frames_start:self.frames_end])

        self.y = np.array([])
        # Sinusoids synthesis (gives 0 values for non-selected regions of the sinusoids)

        for f in range(0, self.frames_end - self.frames_start):  # For every frame
            for i in range(0, len(self.sinusoids2[0])):  # For every bin of the frame
                if self.sinusoids2[f][i] <= self.frequencies_start or self.sinusoids2[f][i] >= self.frequencies_end:
                    self.sinusoids2[f][i] = 0.0

            # Synthesis (with OverlapAdd and IFFT)
            fft_synth = sineSynth(self.magnitudes2[f], self.sinusoids2[f], self.phases2[f])

            out = overl(ifft(fft_synth))

            # Save result
            self.y = np.append(self.y, out)

        # Write the output file to the specified location
        awrite(self.y)

    def plot(self):

        self.spectrogram.setYRange(0, 1025)
        plt.close()
        plt.figure()
        plt.subplot(2, 1, 1)
        # Plotting with Matplotlib in comparison
        plt.pcolormesh(np.transpose(self.spec))
        plt.xlabel("Frames")
        plt.ylabel("Bins")
        plt.colorbar()

        # This plot is not correct I think, maybe for the result of applying the essentia function
        plt.subplot(2, 1, 2)
        if self.sinusoids2.shape[1] > 0:
            self.sinusoids2[self.sinusoids2 <= 0] = np.nan
            plt.plot(self.sinusoids2)
            plt.axis([0, 187, 0, 22000])
            plt.xlabel("Frames")
            plt.ylabel("Frequencies")
            plt.title('frequencies of sinusoidal tracks')

        plt.show()

    def play_result(self):
        sd.play(self.y, fs)

    def stop_result(self):
        sd.stop()
