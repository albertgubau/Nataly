from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow, QWidget, QPushButton, QSlider, QLabel, QLineEdit, QFileDialog, QMessageBox, \
    QComboBox
from PyQt5.QtCore import QRect
import pyqtgraph as pg

from spec_help_window import Ui_SpecHelpWindow

import numpy as np
import essentia.standard as es
import sounddevice as sd


class Sinusoidal_Spec_Anal(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Load the ui file
        uic.loadUi('sinusoidal_spec_anal.ui', self)

        # Initially we will always be on dark mode and the there is no need of showing not applied changes
        self.dark_mode = True
        self.not_applied_changes = False

        # Get widgets and link the callback functions
        self.help_btn = self.findChild(QPushButton, "help_btn")
        self.help_btn.clicked.connect(lambda: self.open_help_window())

        self.combo = self.findChild(QComboBox, "comboBox")
        self.combo.addItem('hamming')
        self.combo.addItem('hann')
        self.combo.setEnabled(False)
        self.combo.currentIndexChanged.connect(lambda: self.changed_inputs())

        self.fft_size_inpt = self.findChild(QLineEdit, "fft_size_inpt")
        self.fft_size_inpt.setEnabled(False)
        self.fft_size_inpt.setText('2048')
        self.fft_size_inpt.textChanged.connect(lambda: self.changed_inputs())

        self.window_size_inpt = self.findChild(QLineEdit, "window_size_inpt")
        self.window_size_inpt.setEnabled(False)
        self.window_size_inpt.setText('2000')
        self.window_size_inpt.textChanged.connect(lambda: self.changed_inputs())

        self.reset_default_btn = self.findChild(QPushButton, "reset_default_btn")
        self.reset_default_btn.setEnabled(False)
        self.reset_default_btn.clicked.connect(lambda: self.reset_default_inpts())

        self.recompute_btn = self.findChild(QPushButton, "recompute_btn")
        self.recompute_btn.setEnabled(False)
        self.recompute_btn.clicked.connect(lambda: self.change_parameters())

        self.changed_inputs_label = self.findChild(QLabel, "changed_params")
        self.changed_inputs_label2 = self.findChild(QLabel, "not_applied_label")
        self.changed_inputs_label2.setStyleSheet('color:#2e2e2e')

        self.browse_button = self.findChild(QPushButton, "browse_btn")
        self.input_text_box = self.findChild(QLineEdit, "filename")
        self.browse_button.clicked.connect(lambda: self.browse_file())

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

        # Initialize analysis/synthesis parameters and sampling rate
        self.fs = 44100
        self.N = int(self.fft_size_inpt.text())
        self.H = self.N // 4
        self.M = int(self.window_size_inpt.text())

        # Instantiate the Essentia Algorithms
        self.w = es.Windowing(type=self.combo.currentText(), size=self.M - 1)
        self.spectrum = es.Spectrum()
        self.fft = es.FFT(size=self.N)
        self.sineAnal = es.SineModelAnal(sampleRate=self.fs,
                                         maxnSines=150,
                                         magnitudeThreshold=-80,
                                         freqDevOffset=10,
                                         freqDevSlope=0.001)

        self.sineSynth = es.SineModelSynth(sampleRate=self.fs, fftSize=self.N, hopSize=self.H)
        self.ifft = es.IFFT(size=self.N)
        self.overl = es.OverlapAdd(frameSize=self.N, hopSize=self.H)

        # Configure pyqtgraph
        pg.setConfigOptions(antialias=True)

        # Initialize plotting widget
        self.win = pg.GraphicsLayoutWidget(self)
        self.win.setGeometry(QRect(90, 160, 700, 371))
        self.win.setBackground('#2e2e2e')

        # Interpret image data as row-major instead of col-major
        pg.setConfigOptions(imageAxisOrder='row-major')

        # Configure spectrum plot axis
        sp_xaxis = pg.AxisItem(orientation='bottom')
        sp_xaxis.setScale(scale=self.H / self.fs)
        sp_yaxis = pg.AxisItem(orientation='left')
        sp_yaxis.setScale(scale=self.fs / self.N)

        # Add plot to the window and configure labels
        self.spectrogram = self.win.addPlot(
            title='SPECTROGRAM', row=1, col=1, axisItems={'bottom': sp_xaxis, 'left': sp_yaxis}
        )

        self.spectrogram.setLabel('bottom', "Time (s)")
        self.spectrogram.setLabel('left', "Frequency (Hz)")

        self.spectrogram.getAxis('left').setTextPen('gray')
        self.spectrogram.getAxis('bottom').setTextPen('gray')

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
        self.roi.setZValue(10)  # Make sure ROI is drawn above image
        self.roi.sigRegionChangeFinished.connect(lambda: self.SelectedRegion())

        # Initialize the algorithms parameters
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

        # Counter of savings to keep track of the file to be saved name
        self.savings = 0

        # Configure the slider widget
        self.slider = self.findChild(QSlider, "verticalSlider")
        self.slider.setEnabled(False)
        self.slider_label = self.findChild(QLabel, "slider_label")

        self.multiplicator = 1.0

        self.slider.valueChanged.connect(self.slide_it)
        self.slider.setMinimum(-1200)
        self.slider.setMaximum(1200)
        self.slider.setValue(0)
        self.slider.sliderReleased.connect(lambda: self.synthesis())

    # Method to change the slider value
    def slide_it(self, value):
        r = 2 ** (1 / 12)
        self.multiplicator = r ** (float(value) / 100)  # Multiplicator as semitones
        self.slider_label.setText("{0:.4g}".format(round(float(value) / 100, 1)))

    # Method to reset the slider value
    def reset_slider(self):
        self.slider.setValue(0)
        self.multiplicator = 1.0
        self.synthesis()

    # Method to keep track of not applied changes option
    def applied_changes(self):
        self.changed_inputs_label.setStyleSheet('')
        if self.dark_mode:
            self.changed_inputs_label2.setStyleSheet('QLabel{'
                                                     'color: #2e2e2e;'
                                                     '}')
        else:
            self.changed_inputs_label2.setStyleSheet('QLabel{'
                                                     'color: #eaebeb;'
                                                     '}')
        self.not_applied_changes = False

    # Method to reset the default analysis/synthesis parameters
    def reset_default_inpts(self):
        self.window_size_inpt.setText('2000')
        self.fft_size_inpt.setText('2048')
        self.combo.setCurrentIndex(0)

    # Method to keep track of changed parameters on the inputs
    def changed_inputs(self):  # Adds an amber color to make the user notice the non-applied changes

        self.not_applied_changes = True
        self.changed_inputs_label.setStyleSheet('QLabel{'
                                                'background-color:rgb(255, 190, 111);'
                                                'border-radius:10px;'
                                                '}')

        self.changed_inputs_label2.setStyleSheet('QLabel{'
                                                 'background-color: #2e2e2e;'
                                                 'border-radius:10px;'
                                                 'color: rgb(255, 190, 111);'
                                                 '}')

    # Method to browse a sound file
    def browse_file(self):

        # Open File Dialog (returns a tuple)
        fname = QFileDialog.getOpenFileName(None, "Open File", "", "All Files (*)",
                                            options=QFileDialog.DontUseNativeDialog)

        # Output filename to screen
        if fname:
            try:
                self.x = es.MonoLoader(filename=str(fname[0]))()

            except RuntimeError:  # Error management (open a dialog)
                dialog = QMessageBox(self)
                dialog.setText('Yo have not loaded any file or the file you have loaded is not an audio file, '
                               'please load an audio file to analyze it through its spectrogram.')
                dialog.setWindowTitle('No file loaded!')

                if self.dark_mode:
                    dialog.setStyleSheet('background-color:#2e2e2e;'
                                         'color:white;')
                else:
                    dialog.setStyleSheet('background-color:#dbdbdb;'
                                         'color:black;')
                dialog.exec_()
                return None  # Go back in case of an error

            self.input_text_box.setText(str(fname[0]))  # Modifiy the input text box with the filepath

            # Enable buttons when a file is loaded
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
            self.reset_default_btn.setEnabled(True)

            # Clear the plot
            self.img.clear()

            # Reset the spec and sinusoids arrays
            self.spec = np.array([])
            self.sinusoids = np.array([])

            # Compute
            self.compute()

    # Method to be called whenever an analysis/synthesis parameter is changed
    def change_parameters(self):

        try:
            # Get the new parameters
            self.N = int(self.fft_size_inpt.text())
            self.H = self.N // 4
            self.M = int(self.window_size_inpt.text())

            # Re-instantiate the Essentia Algorithms
            self.w = es.Windowing(type=self.combo.currentText(), size=self.M - 1)
            self.spectrum = es.Spectrum()
            self.fft = es.FFT(size=self.N)
            self.sineAnal = es.SineModelAnal(sampleRate=self.fs,
                                             maxnSines=150,
                                             magnitudeThreshold=-80,
                                             freqDevOffset=10,
                                             freqDevSlope=0.001)

            self.sineSynth = es.SineModelSynth(sampleRate=self.fs, fftSize=self.N, hopSize=self.H)
            self.ifft = es.IFFT(size=self.N)
            self.overl = es.OverlapAdd(frameSize=self.N, hopSize=self.H)

            # Change the axis of the spectrogram plot
            sp_xaxis = pg.AxisItem(orientation='bottom')
            sp_xaxis.setScale(scale=self.H / self.fs)
            sp_yaxis = pg.AxisItem(orientation='left')
            sp_yaxis.setScale(scale=self.fs / self.N)

            self.spectrogram.setAxisItems(axisItems={'bottom': sp_xaxis, 'left': sp_yaxis})
            self.spectrogram.setLabel('bottom', "Time (s)")
            self.spectrogram.setLabel('left', "Frequency (Hz)")

            # Re-compute
            self.compute()

            # Call the applied changes function
            self.applied_changes()

        # If the parameters are wrong set up an error dialog
        except (RuntimeError, ValueError) as e:
            dialog = QMessageBox(self)
            dialog.setText(str(e))
            dialog.setWindowTitle('Wrong analysis parameters!')
            if self.dark_mode:
                dialog.setStyleSheet('background-color:#2e2e2e;'
                                     'color:white;')
            else:
                dialog.setStyleSheet('background-color:#dbdbdb;'
                                     'color:black;')
            dialog.exec_()

    # Compute analysis/synthesis method
    def compute(self):

        frames = 0  # Frame counter

        # Loop to iterate through the sliced frame by frame audio
        for frame in es.FrameGenerator(audio=self.x, frameSize=self.N, hopSize=self.H, startFromZero=True):

            frame_spectrum = self.spectrum(self.w(frame))  # Compute the spectrum

            infft = self.fft(self.w(frame))  # Compute FFT

            sine_anal = self.sineAnal(infft)  # Compute Sinusoidal Analysis

            if frames == 0:  # First frame (catch all the data as first)
                self.spec = frame_spectrum
                self.sinusoids = np.array([sine_anal[0]])
                self.magnitudes = np.array([sine_anal[1]])
                self.phases = np.array([sine_anal[2]])

            else:  # Next frames (stack the data with the previous one)
                self.spec = np.vstack((self.spec, frame_spectrum))
                self.sinusoids = np.vstack((self.sinusoids, np.array([sine_anal[0]])))
                self.magnitudes = np.vstack((self.magnitudes, np.array([sine_anal[1]])))
                self.phases = np.vstack((self.phases, np.array([sine_anal[2]])))

            frames += 1  # Keep counter of frames

        # Fit the min and max levels of the histogram to the data available
        self.hist.setLevels(np.min(self.spec), np.max(self.spec))

        # Restore the gradient state of the histogram
        self.hist.gradient.restoreState(
            {'mode': 'rgb',
             'ticks': [(0.5, (0, 182, 188, 255)),
                       (1.0, (246, 111, 0, 255)),
                       (0.0, (75, 0, 113, 255))]})

        # Transpose the computed spec to plot it
        spectrogram = np.transpose(self.spec)

        # Set the spectrogram to be plotted
        self.img.setImage(spectrogram)

        # Set up the correct scaling for y-axis
        self.spectrogram.setYRange(0, 300)
        self.spectrogram.setXRange(0, np.transpose(self.spec)[0, :].size)

        # Set Region of Interest position to plot start (bottom-left)
        self.roi.setPos(0, 0)

    # Method to get map the ROI selected and the spectrogram data
    def SelectedRegion(self):

        # returnMappedCoords=True gives us the spectrogram indexes (self.indexes) where the ROI is placed
        self.selected, self.indexes = self.roi.getArrayRegion(self.img.image, self.img, returnMappedCoords=True)

        # We get the starting and ending frames from the ROI
        self.frames_start = int(self.indexes[1][0][0])
        self.frames_end = int(self.indexes[1][-1][-1])

        # If the ROI is outside the spectrogram from the left we select from the first spectrogram frame
        if self.frames_start <= 0:
            self.frames_start = 0

        # Get the number of frames
        numFrames = np.transpose(self.spec)[0, :].size

        # If the ROI is outside the spectrogram from the right we select from the last spectrogram frame
        if self.frames_end >= numFrames:
            self.frames_end = numFrames

        # Get the starting and ending bins from ROI
        self.bins_start = int(self.indexes[0][0][0])
        self.bins_end = int(self.indexes[0][-1][0])

        # If the ROI is outside the spectrogram from the bottom we select from the first spectrogram bin
        if self.bins_start <= 0:
            self.bins_start = 0

        # Get the number of bins
        numFreqs = np.transpose(self.spec)[:, 0].size

        # If the ROI is outside the spectrogram from the top we select from the last spectrogram bin
        if self.bins_end >= numFreqs:
            self.bins_end = numFreqs

        # Convert it to frequency values
        self.frequencies_start = (self.bins_start * self.fs) / self.N
        self.frequencies_end = (self.bins_end * self.fs) / self.N

        # Compute synthesis
        self.synthesis()

    def synthesis(self):

        # Copy the sinusoids from the initial full analysis and cut it to take into account only the ROI
        self.sinusoids2 = np.copy(self.sinusoids[self.frames_start:self.frames_end])
        self.magnitudes2 = np.copy(self.magnitudes[self.frames_start:self.frames_end])
        self.phases2 = np.copy(self.phases[self.frames_start:self.frames_end])

        # Initialize synthesis result
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

    # Method to play the original sound
    def play_original(self):
        sd.play(self.x, self.fs)

    # Method to stop playing the original sound
    def stop_original(self):
        sd.stop()

    # Method to play the resulting sound from synthesis
    def play_result(self):
        sd.play(self.y, self.fs)

    # Method to stop playing the resulting sound from synthesis
    def stop_result(self):
        sd.stop()

    # Method to save the resulting synthesized audio
    def save_result(self):
        filename = 'output_synthesis_' + str(self.savings) + '.wav'  # Keep track how many savings we made
        awrite = es.MonoWriter(filename=filename, sampleRate=self.fs)
        awrite(self.y)
        self.savings += 1

        dialog = QMessageBox(self)
        dialog.setText('File saved as ' + filename)
        dialog.setWindowTitle('File saved!')
        dialog.setStyleSheet('color:white;')
        if self.dark_mode:
            dialog.setStyleSheet('background-color:#2e2e2e;'
                                 'color:white;')
        else:
            dialog.setStyleSheet('background-color:#dbdbdb;'
                                 'color:black;')
        dialog.exec_()

    # Method in charge of changing the stylesheet of the window to change the theme of the application
    def change_theme(self):
        if self.dark_mode:
            self.win.setBackground('#2e2e2e')
            self.spectrogram.getAxis('left').setTextPen('gray')
            self.spectrogram.getAxis('bottom').setTextPen('gray')
            if not self.not_applied_changes:
                self.changed_inputs_label2.setStyleSheet('color:#2e2e2e')
        else:
            self.win.setBackground('#eaebeb')
            self.spectrogram.getAxis('left').setTextPen('black')
            self.spectrogram.getAxis('bottom').setTextPen('black')
            if not self.not_applied_changes:
                self.changed_inputs_label2.setStyleSheet('color:#eaebeb')

    # Method to open a help window
    def open_help_window(self):
        self.window = QMainWindow()
        self.ui = Ui_SpecHelpWindow()
        self.ui.setupUi(self.window)
        self.window.show()

