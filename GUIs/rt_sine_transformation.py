import numpy as np
import essentia.standard as es
import struct
import pyaudio
import sounddevice as sd

from PyQt5 import uic
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore
from PyQt5.QtWidgets import QMainWindow, QWidget, QPushButton, QSlider, QLabel, QCheckBox, QMessageBox
from PyQt5.QtCore import QRect

from GUIs.rt_sine_help_window import Ui_RTSineHelpWindow

# Global attributes
fs = 44100

# Instantiate the Essentia Algorithms
w = es.Windowing(type='hamming', size=2001)
fft = es.FFT(size=2048)
sineAnal = es.SineModelAnal(sampleRate=fs,
                            maxnSines=150,
                            magnitudeThreshold=-80,
                            freqDevOffset=10,
                            freqDevSlope=0.001)

sineSynth = es.SineModelSynth(sampleRate=fs, fftSize=2048, hopSize=512)
ifft = es.IFFT(size=2048)
overl = es.OverlapAdd(frameSize=2048, hopSize=512)


class Rt_sine_transformation(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Load the ui file
        uic.loadUi('GUIs/rt_sine_transformation.ui', self)

        # Set dark mode to True
        self.dark_mode = True

        # Configure plot
        pg.setConfigOptions(antialias=True)
        self.win = pg.GraphicsLayoutWidget(self)
        self.win.setGeometry(QRect(120, 80, 841, 450))
        self.win.setBackground('#2e2e2e')

        # Get the widgets and connect their callbacks
        self.help_btn = self.findChild(QPushButton, "help_btn")
        self.help_btn.clicked.connect(lambda: self.open_help_window())

        self.record_button = self.findChild(QPushButton, "record_btn")
        self.record_button.clicked.connect(lambda: self.record())

        # Get the slider and configure it
        self.slider = self.findChild(QSlider, "verticalSlider")
        self.label = self.findChild(QLabel, "label")

        self.multiplicator = 1.0
        self.slider.valueChanged.connect(self.slide_it)
        self.slider.setMinimum(-1200)
        self.slider.setMaximum(1200)
        self.slider.setValue(0)

        self.listen_checkbox = self.findChild(QCheckBox, "listen_checkbox")

        # Set the recording mode to false
        self.recording = False

        self.red_border = self.findChild(QLabel, "red_border")
        self.recording_label = self.findChild(QLabel, "recording_label")
        self.recording_circle = self.findChild(QPushButton, "recording_circle")

        self.reset_button = self.findChild(QPushButton, "reset_btn")
        self.reset_button.clicked.connect(lambda: self.reset_slider())

        # Initialize a traces dictinoary
        self.traces = dict()

        # Initialize resulting arrays
        self.y = []
        self.frames = []
        self.result = np.array(0)
        self.results = np.array([])

        # Waveform x/y axis labels
        wf_xlabels = [(0, '0'), (2048, '2048')]
        wf_xaxis = pg.AxisItem(orientation='bottom')
        wf_xaxis.setTicks([wf_xlabels])
        wf_yaxis = pg.AxisItem(orientation='left')

        # Spectrum x/y axis labels
        sp_xlabels = [
            (np.log10(10), '10'), (np.log10(100), '100'),
            (np.log10(1000), '1000'), (np.log10(22050), '22050')
        ]
        sp_xaxis = pg.AxisItem(orientation='bottom')
        sp_xaxis.setTicks([sp_xlabels])

        # Add plots to the window and configure it
        self.waveform = self.win.addPlot(
            title='WAVEFORM', row=0, col=0, axisItems={'bottom': wf_xaxis, 'left': wf_yaxis},
        )
        self.waveform.hideAxis('left')
        self.waveform.hideAxis('bottom')

        self.win.ci.layout.setSpacing(30)

        self.spectrum = self.win.addPlot(
            title='SPECTRUM', row=2, col=0, axisItems={'bottom': sp_xaxis},
        )

        self.spectrum.hideAxis('left')

        # Keep iterations count to know if we need an auxiliary frame or not from the audio (ensure hops)
        self.iterations = 0
        self.wf_data = np.array([])
        self.listening = False

        # PyAudio stream initialization
        self.FORMAT = pyaudio.paFloat32  # Floats as data captured
        self.CHANNELS = 1  # Mono
        self.RATE = fs  # Sampling rate in Hz (samples/second)
        self.CHUNK = 2048  # Number of samples per frame (audio frame with frameSize = 2048)

        self.p = pyaudio.PyAudio()  # Instance pyAudio class

        self.stream = self.p.open(  # Create the data stream with the previous parameters
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            output=True,
            frames_per_buffer=self.CHUNK,
        )

        # Waveform and Spectrum x-axis points (bins and Hz)
        self.freqs = np.arange(0, self.CHUNK)
        # Half spectrum because of essentia computation
        self.f = np.linspace(0, self.RATE // 2, self.CHUNK // 2 + 1)  # 1025 numbers from 0 to 22050 (frequencies)

        # Counter to change the recording button state and appearance of window when recording
        self.counter = 0
        self.recordings = 0

    # Callback for when the recording button is pressed
    def record(self):
        self.counter += 1
        self.recording = not self.recording

        # If we were not recording now we are so change the style of the button and the window
        if self.recording:
            self.red_border.setStyleSheet("border:2px solid red;"
                                          "border-radius:10px;")
            self.recording_label.setStyleSheet("color: red;")
            self.recording_circle.setStyleSheet("background-color: rgb(237, 51, 59);"
                                                "border-radius:8px;")
            self.record_button.setText("STOP")

        # If we were recording we stop recording and save the result
        if self.counter % 2 == 0:
            self.recordings += 1
            self.red_border.setStyleSheet("border:none;")
            if self.dark_mode:
                self.recording_label.setStyleSheet("color: #2e2e2e;")
                self.recording_circle.setStyleSheet("background-color:#2e2e2e")
            else:
                self.recording_label.setStyleSheet("color: #eaebeb;")
                self.recording_circle.setStyleSheet("background-color:#eaebeb")
            self.record_button.setText("Record")
            self.saveResult()

    # Method to change the value of the slider
    def slide_it(self, value):
        r = 2 ** (1 / 12)
        self.multiplicator = r ** (float(value) / 100)  # Keep the value of the multiplicator with semitones
        self.label.setText("{0:.4g}".format(round(float(value) / 100, 1)))

    # Method to reset the slider value
    def reset_slider(self):
        self.slider.setValue(0)
        self.multiplicator = 1.0

    # Method to set the data for the different plots
    def set_plotdata(self, name, data_x, data_y):

        # If it is the first time of the plot we set a new one, if not we set the data to it
        if name in self.traces:
            self.traces[name].setData(data_x, data_y)

        else:
            if name == 'waveform':
                self.traces[name] = self.waveform.plot(pen='c', width=3)
                #self.waveform.setYRange(-0.05, 0.05, padding=0)

            if name == 'spectrum':
                self.traces[name] = self.spectrum.plot(pen='m', width=3)
                self.spectrum.setLogMode(x=True, y=True)
                #self.spectrum.setYRange(np.log10(0.001), np.log10(20), padding=0)

    # Method to update the plots iteratively
    def update_plots(self):

        # We get parts of the previous frame data to ensure the hop between frames (H=512)
        previous_wf_data1 = self.wf_data[511:2048]
        previous_wf_data2 = self.wf_data[1023:2048]
        previous_wf_data3 = self.wf_data[1535:2048]

        # Get the data from the mic
        self.wf_data = self.stream.read(self.CHUNK, exception_on_overflow=False)

        # Unpack the data as floats
        self.wf_data = np.array(
            struct.unpack(str(self.CHUNK) + 'f',
                          self.wf_data))  # str(self.CHUNK) + 'f' denotes size and type of data

        # Plot a captured 2048 samples frame from the mic
        self.set_plotdata(name='waveform', data_x=self.freqs, data_y=self.wf_data)

        # Apply FFT to the windowed frame
        fft_signal = fft(w(self.wf_data))

        # Sine Analysis to the FFT signal to get tfreq for the current frame
        sine_anal = sineAnal(fft_signal)

        # Frequency scaling values
        ysfreq = sine_anal[0] * self.multiplicator  # Scale of frequencies (where the magic happens)

        # Sinusoidal Synthesis (with OverlapAdd and IFFT)
        fft_synth = sineSynth(sine_anal[1], ysfreq, sine_anal[2])

        # Set the spectrum data and plot it
        sp_data = np.abs(fft(self.wf_data))
        self.set_plotdata(name='spectrum', data_x=self.f, data_y=sp_data)

        # If we are not in the first iteration of the computations, we need to get auxiliary data to ensure H=512
        if self.iterations != 0:

            # First auxiliary waveform
            wf_data1 = np.append(previous_wf_data1, self.wf_data[1:512])

            fft1 = fft(w(wf_data1))
            sine_anal1 = sineAnal(fft1)
            ysfreq1 = sine_anal1[0] * self.multiplicator
            fft_synth1 = sineSynth(sine_anal1[1], ysfreq1, sine_anal1[2])

            out1 = overl(ifft(fft_synth1))  # We have a 512 samples frame

            # Second auxiliary waveform
            wf_data2 = np.append(previous_wf_data2, self.wf_data[1:1024])

            fft2 = fft(w(wf_data2))
            sine_anal2 = sineAnal(fft2)
            ysfreq2 = sine_anal2[0] * self.multiplicator
            fft_synth2 = sineSynth(sine_anal2[1], ysfreq2, sine_anal2[2])

            out2 = overl(ifft(fft_synth2))  # We have a 512 samples frame

            # Third auxiliary waveform
            wf_data3 = np.append(previous_wf_data3, self.wf_data[1:1536])

            fft3 = fft(w(wf_data3))
            sine_anal3 = sineAnal(fft3)
            ysfreq3 = sine_anal3[0] * self.multiplicator
            fft_synth3 = sineSynth(sine_anal3[1], ysfreq3, sine_anal3[2])

            out3 = overl(ifft(fft_synth3))  # We have a 512 samples frame

            # We append all the auxilary waveforms, and we append also the result to the results array
            self.results = np.append(np.append(out1, out2), out3)
            self.result = np.append(self.result, self.results)

        out = overl(ifft(fft_synth))  # Compute the resulting array

        # Save result and play it simultaneously
        self.result = np.append(self.result, out)

        # If we are recording, we capture the result in another array to not lose it in the following cut
        if self.recording:
            self.result2 = self.result

        # We cut the signal to not lag the program with large arrays while we are not recording
        if len(self.result) >= 4097 and not self.recording:
            self.result = self.result[len(self.result) - 4096:]

        # If we are in the Real-Time Sine Transformations window and the listening checkbox is checked
        # we play the sound
        if self.listening and self.listen_checkbox.isChecked():
            sd.play(np.array(self.result[len(self.result) - 4096:]), fs)
        self.iterations = 1

    # Method that ensure the real-time visualization by using a QTimer and calling the update plots method
    def animation(self):
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plots)
        self.timer.start(0)

    # Method to save the result
    def saveResult(self):
        filename = 'output_rt_sinusoidal_' + str(self.recordings) + '.wav'  # Keep track of the number of recordings
        awrite = es.MonoWriter(filename=filename, sampleRate=fs)
        awrite(self.result2)

        # Set up a dialog to inform the user that their file is saved correctly
        dialog = QMessageBox(self)
        dialog.setText('File saved as ' + filename)
        dialog.setWindowTitle('File saved!')
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
            if not self.recording:
                self.recording_label.setStyleSheet('color: #2e2e2e')
                self.recording_circle.setStyleSheet('background-color:#2e2e2e')
        else:
            self.win.setBackground('#eaebeb')
            if not self.recording:
                self.recording_label.setStyleSheet('color: #eaebeb')
                self.recording_circle.setStyleSheet('background-color:#eaebeb')

    # Method to open a help window
    def open_help_window(self):
        self.window = QMainWindow()
        self.ui = Ui_RTSineHelpWindow()
        self.ui.setupUi(self.window)
        self.window.show()