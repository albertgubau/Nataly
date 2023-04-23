from PyQt5 import uic
from PyQt5.QtWidgets import QWidget, QPushButton, QSlider, QLabel, QLineEdit, QFileDialog, QMessageBox, QComboBox
from PyQt5.QtCore import QRect
import pyqtgraph as pg

import numpy as np
# import matplotlib.pyplot as plt
import essentia.standard as es
import sounddevice as sd

fs = 44100
N = 2048
H = N // 4


class Sinusoidal_Spec_Anal(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        uic.loadUi('sinusoidal_spec_anal.ui', self)

        self.fft_size_inpt = self.findChild(QLineEdit, "fft_size_inpt")
        self.fft_size_inpt.setEnabled(False)
        self.fft_size_inpt.setText('2048')
        self.window_size_inpt = self.findChild(QLineEdit, "window_size_inpt")
        self.window_size_inpt.setEnabled(False)
        self.window_size_inpt.setText('2000')

        self.recompute_btn = self.findChild(QPushButton, "recompute_btn")
        self.recompute_btn.setEnabled(False)
        self.recompute_btn.clicked.connect(lambda: self.change_parameters())

        self.browse_button = self.findChild(QPushButton, "browse_btn")
        self.input_text_box = self.findChild(QLineEdit, "filename")
        self.browse_button.clicked.connect(lambda: self.browse_file())

        self.combo = self.findChild(QComboBox, "comboBox")
        self.combo.addItem('hamming')
        self.combo.addItem('hann')
        self.combo.setEnabled(False)

        # self.compute_button = self.findChild(QPushButton, "compute_btn")
        # self.compute_button.clicked.connect(lambda: self.plot())

        self.play_original_button = self.findChild(QPushButton, "play_original_btn")
        self.play_original_button.setEnabled(False)
        self.play_original_button.clicked.connect(lambda: self.play_original())

        self.pause_original_button = self.findChild(QPushButton, "pause_original_btn")
        self.pause_original_button.setEnabled(False)
        self.pause_original_button.clicked.connect(lambda: self.stop_original())

        self.play_button = self.findChild(QPushButton, "play_btn")
        self.play_button.setEnabled(False)
        self.play_button.clicked.connect(lambda: self.play_result())

        self.pause_button = self.findChild(QPushButton, "pause_btn")
        self.pause_button.setEnabled(False)
        self.pause_button.clicked.connect(lambda: self.stop_result())

        self.save_button = self.findChild(QPushButton, "save_btn")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(lambda: self.save_result())

        self.reset_button = self.findChild(QPushButton, "reset_btn")
        self.reset_button.setEnabled(False)
        self.reset_button.clicked.connect(lambda: self.reset_slider())

        self.N = int(self.fft_size_inpt.text())
        self.H = N // 4
        self.M = int(self.window_size_inpt.text())

        # Instantiate the Essentia Algorithms
        self.w = es.Windowing(type=self.combo.currentText(), size=self.M - 1)
        self.spectrum = es.Spectrum()
        self.fft = es.FFT(size=self.N)
        self.sineAnal = es.SineModelAnal(sampleRate=fs,
                                         maxnSines=150,
                                         magnitudeThreshold=-80,
                                         freqDevOffset=10,
                                         freqDevSlope=0.001)

        self.sineSynth = es.SineModelSynth(sampleRate=fs, fftSize=self.N, hopSize=self.H)
        self.ifft = es.IFFT(size=self.N)
        self.overl = es.OverlapAdd(frameSize=self.N, hopSize=self.H)

        pg.setConfigOptions(antialias=True)

        self.win = pg.GraphicsLayoutWidget(self)
        self.win.setGeometry(QRect(90, 160, 700, 371))
        self.win.setBackground('#2e2e2e')

        # Interpret image data as row-major instead of col-major
        pg.setConfigOptions(imageAxisOrder='row-major')

        sp_xaxis = pg.AxisItem(orientation='bottom')
        sp_xaxis.setScale(scale=self.H / fs)
        sp_yaxis = pg.AxisItem(orientation='left')
        sp_yaxis.setScale(scale=fs / self.N)

        # Add plots to the window
        self.spectrogram = self.win.addPlot(
            title='SPECTROGRAM', row=1, col=1, axisItems={'bottom': sp_xaxis, 'left': sp_yaxis}
        )

        self.spectrogram.setLabel('bottom', "Time (s)")
        self.spectrogram.setLabel('left', "Frequency (Hz)")

        # Item for displaying image data
        self.img = pg.ImageItem()
        self.spectrogram.addItem(self.img)

        # Add a histogram with which to control the gradient of the image
        self.hist = pg.HistogramLUTItem()
        # Link the histogram to the image
        self.hist.setImageItem(self.img)
        # If you don't add the histogram to the window, it stays invisible, but I find it useful.
        self.win.addItem(self.hist, row=1, col=2)

        # Custom ROI for selecting an image region
        self.roi = pg.ROI([50, 50], [100, 200], pen='r', handlePen='g', handleHoverPen='b')
        self.roi.addScaleHandle([1, 1], [0, 0])
        self.roi.addScaleHandle([0, 0], [1, 1])
        self.roi.addScaleHandle([0, 1], [1, 0])
        self.roi.addScaleHandle([1, 0], [0, 1])
        self.spectrogram.addItem(self.roi)
        self.roi.setZValue(10)  # make sure ROI is drawn above image
        self.roi.sigRegionChangeFinished.connect(lambda: self.SelectedRegion())

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

        self.savings = 0

        self.slider = self.findChild(QSlider, "verticalSlider")
        self.slider.setEnabled(False)
        self.slider_label = self.findChild(QLabel, "slider_label")

        self.multiplicator = 1.0

        self.slider.valueChanged.connect(self.slide_it)
        self.slider.setMinimum(50)
        self.slider.setMaximum(200)
        self.slider.setValue(100)
        self.slider.sliderReleased.connect(lambda: self.synthesis())

    def slide_it(self, value):
        self.multiplicator = float(value) / 100
        self.slider_label.setText("{0:.4g}".format(self.multiplicator))

    def browse_file(self):

        # Open File Dialog (returns a tuple)
        fname = QFileDialog.getOpenFileName(self, "Open File", "", "All Files (*)",
                                            options=QFileDialog.DontUseNativeDialog)

        # Output filename to screen
        if fname:
            try:
                self.x = es.MonoLoader(filename=str(fname[0]))()

            except RuntimeError as e:
                dialog = QMessageBox(self)
                dialog.setText('Yo have not loaded any file or the file you have loaded is not an audio file, '
                               'please load an audio file to analyze its spectrogram.')
                dialog.setWindowTitle('No file loaded!')
                dialog.setStyleSheet('color:white;')
                dialog.exec_()
                return None

            self.input_text_box.setText(str(fname[0]))  # We should modifiy the input text box

            self.play_original_button.setEnabled(True)
            self.pause_original_button.setEnabled(True)
            self.play_button.setEnabled(True)
            self.pause_button.setEnabled(True)
            self.save_button.setEnabled(True)
            self.slider.setEnabled(True)
            self.reset_button.setEnabled(True)
            self.fft_size_inpt.setEnabled(True)
            self.window_size_inpt.setEnabled(True)
            self.recompute_btn.setEnabled(True)
            self.combo.setEnabled(True)

            self.img.clear()

            self.spec = np.array([])
            self.sinusoids = np.array([])

            self.compute()

    def change_parameters(self):

        self.N = int(self.fft_size_inpt.text())
        self.H = N // 4
        self.M = int(self.window_size_inpt.text())

        # Instantiate the Essentia Algorithms
        self.w = es.Windowing(type=self.combo.currentText(), size=self.M - 1)
        self.spectrum = es.Spectrum()
        self.fft = es.FFT(size=N)
        self.sineAnal = es.SineModelAnal(sampleRate=fs,
                                         maxnSines=150,
                                         magnitudeThreshold=-80,
                                         freqDevOffset=10,
                                         freqDevSlope=0.001)

        self.sineSynth = es.SineModelSynth(sampleRate=fs, fftSize=N, hopSize=H)
        self.ifft = es.IFFT(size=N)
        self.overl = es.OverlapAdd(frameSize=N, hopSize=H)

        sp_xaxis = pg.AxisItem(orientation='bottom')
        sp_xaxis.setScale(scale=self.H / fs)
        sp_yaxis = pg.AxisItem(orientation='left')
        sp_yaxis.setScale(scale=fs / self.N)

        self.spectrogram.setAxisItems(axisItems={'bottom': sp_xaxis, 'left': sp_yaxis})
        self.spectrogram.setLabel('bottom', "Time (s)")
        self.spectrogram.setLabel('left', "Frequency (Hz)")

        self.compute()

    def compute(self):

        frames = 0
        for frame in es.FrameGenerator(audio=self.x, frameSize=self.N, hopSize=self.H, startFromZero=True):

            frame_spectrum = self.spectrum(self.w(frame))

            infft = self.fft(self.w(frame))

            sine_anal = self.sineAnal(infft)

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
            fft_synth = self.sineSynth(self.magnitudes2[f], self.sinusoids2[f] * self.multiplicator, self.phases2[f])

            out = self.overl(self.ifft(fft_synth))

            # Save result
            self.y = np.append(self.y, out)

    # def plot(self):
    #
    #    self.spectrogram.setYRange(0, 1025)
    #    plt.close()
    #    plt.figure()
    #    plt.subplot(2, 1, 1)
    #    # Plotting with Matplotlib in comparison
    #    plt.pcolormesh(np.transpose(self.spec))
    #    plt.xlabel("Frames")
    #    plt.ylabel("Bins")
    #    plt.colorbar()
    #
    #    # This plot is not correct I think, maybe for the result of applying the essentia function
    #    plt.subplot(2, 1, 2)
    #    if self.sinusoids2.shape[1] > 0:
    #        self.sinusoids2[self.sinusoids2 <= 0] = np.nan
    #        plt.plot(self.sinusoids2)
    #        plt.axis([0, 187, 0, 22000])
    #        plt.xlabel("Frames")
    #        plt.ylabel("Frequencies")
    #        plt.title('frequencies of sinusoidal tracks')
    #
    #    plt.show()


    def play_original(self):
        sd.play(self.x,fs)

    def stop_original(self):
        sd.stop()

    def play_result(self):
        sd.play(self.y, fs)

    def stop_result(self):
        sd.stop()

    def save_result(self):
        filename = 'output_synthesis_' + str(self.savings) + '.wav'
        awrite = es.MonoWriter(filename=filename, sampleRate=fs)
        awrite(self.y)
        self.savings += 1
        dialog = QMessageBox(self)
        dialog.setText('File saved as ' + filename)
        dialog.setWindowTitle('File saved!')
        dialog.setStyleSheet('color:white;')
        dialog.exec_()

    def reset_slider(self):
        self.slider.setValue(100)
        self.multiplicator = 1
        self.synthesis()
