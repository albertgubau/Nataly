import numpy as np
import essentia.standard as es
import struct
import pyaudio
import sounddevice as sd

from PyQt5 import uic
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore
from PyQt5.QtWidgets import QWidget, QPushButton, QSlider, QLabel, QCheckBox, QMessageBox
from PyQt5.QtCore import QRect

fs = 44100


# Instantiate the Essentia Algorithms
w = es.Windowing(type='hamming', size=2048)
fft = es.FFT(size=2048)
sineAnal = es.SineModelAnal(sampleRate=fs,
                            maxnSines=150,
                            magnitudeThreshold=-120,
                            freqDevOffset=10,
                            freqDevSlope=0.001)

sineSynth = es.SineModelSynth(sampleRate=fs, fftSize=2048, hopSize=512)
ifft = es.IFFT(size=2048)
overl = es.OverlapAdd(frameSize=2048, hopSize=512)


class Rt_sine_transformation(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        uic.loadUi('rt_sine_transformation.ui', self)

        pg.setConfigOptions(antialias=True)
        self.win = pg.GraphicsLayoutWidget(self)
        self.win.setGeometry(QRect(120, 80, 801, 450))
        self.win.setBackground('#2e2e2e')

        self.record_button = self.findChild(QPushButton, "record_btn")
        self.record_button.clicked.connect(lambda: self.record())

        self.slider = self.findChild(QSlider, "verticalSlider")
        self.label = self.findChild(QLabel, "label")

        self.multiplicator = 1.0
        self.slider.valueChanged.connect(self.slide_it)
        self.slider.setMinimum(50)
        self.slider.setMaximum(200)
        self.slider.setValue(100)

        self.listen_checkbox = self.findChild(QCheckBox, "listen_checkbox")

        self.recording = False

        self.red_border = self.findChild(QLabel, "red_border")
        self.recording_label = self.findChild(QLabel, "recording_label")

        self.reset_button = self.findChild(QPushButton, "reset_btn")
        self.reset_button.clicked.connect(lambda: self.reset_slider())


        # OLD CODE FROM PREVIOUS APP
        self.traces = dict()

        self.y = []
        self.frames = []
        self.result = np.array(0)
        self.results = np.array([])

        # Waveform x/y axis labels
        wf_xlabels = [(0, '0'), (2048, '2048')]
        wf_xaxis = pg.AxisItem(orientation='bottom')
        wf_xaxis.setTicks([wf_xlabels])
        wf_yaxis = pg.AxisItem(orientation='left')

        # Windowed Waveform x/y axis labels
        #wf_w_xlabels = [(0, '0'), (2048, '2048')]
        #wf_w_xaxis = pg.AxisItem(orientation='bottom')
        #wf_w_xaxis.setTicks([wf_w_xlabels])
        #wf_w_yaxis = pg.AxisItem(orientation='left')

        # Out Waveform x/y axis labels
        #out_xlabels = [(0, '0'), (2048, '2048')]
        #out_xaxis = pg.AxisItem(orientation='bottom')
        #out_xaxis.setTicks([out_xlabels])
        #out_yaxis = pg.AxisItem(orientation='left')

        # Spectrum x/y axis labels
        sp_xlabels = [
            (np.log10(10), '10'), (np.log10(100), '100'),
            (np.log10(1000), '1000'), (np.log10(22050), '22050')
        ]
        sp_xaxis = pg.AxisItem(orientation='bottom')
        sp_xaxis.setTicks([sp_xlabels])

        # Add plots to the window
        self.waveform = self.win.addPlot(
            title='WAVEFORM', row=0, col=0, axisItems={'bottom': wf_xaxis, 'left': wf_yaxis},
        )
        self.waveform.hideAxis('left')
        self.waveform.hideAxis('bottom')
        # Add plots to the window
        #self.w_waveform = self.win.addPlot(
        #    title='Windowed WAVEFORM', row=1, col=0, axisItems={'bottom': wf_w_xaxis, 'left': wf_w_yaxis},
        #)
        #self.w_waveform.hideAxis('left')
        #self.w_waveform.hideAxis('bottom')

        self.win.ci.layout.setSpacing(30)

        self.spectrum = self.win.addPlot(
            title='SPECTRUM', row=2, col=0, axisItems={'bottom': sp_xaxis},
        )

        self.spectrum.hideAxis('left')


        #self.out = self.win.addPlot(
        #    title='OUT', row=3, col=0, axisItems={'bottom': out_xaxis, 'left': out_yaxis},
        #)

        #self.out.hideAxis('left')
        #self.out.hideAxis('bottom')

        self.iterations = 0
        self.wf_data = np.array([])
        self.listening = False

        # self.prova = np.array([])

        # PyAudio Stuff
        self.FORMAT = pyaudio.paFloat32
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
        # Waveform and Spectrum x-axis points (bins and Hz)
        self.z = np.arange(0, self.CHUNK)
        # Waveform and Spectrum x-axis points (bins and Hz)
        self.j = np.arange(0, 512)
        # Half spectrum because of essentia computation
        self.f = np.linspace(0, self.RATE // 2, self.CHUNK // 2 + 1)  # 1025 numbers from 0 to 22050 (frequencies)

        self.counter = 0
        self.recordings = 0
    def record(self):

        self.counter += 1
        self.recording = not self.recording

        if(self.recording):
            self.red_border.setStyleSheet("border: 3px solid red;")
            self.recording_label.setStyleSheet("color: red;")
            self.record_button.setText("STOP")

        if(self.counter%2 == 0):
            self.recordings+=1
            self.red_border.setStyleSheet("border:none;")
            self.recording_label.setStyleSheet("color: #2e2e2e;")
            self.record_button.setText("Record")
            self.saveResult()

    def slide_it(self, value):
        self.multiplicator = float(value) / 100
        self.label.setText("{0:.4g}".format(self.multiplicator))

    def reset_slider(self):
        self.slider.setValue(100)
        self.multiplicator = 1

    def set_plotdata(self, name, data_x, data_y):

        if name in self.traces:
            self.traces[name].setData(data_x, data_y)

        else:
            if name == 'waveform':
                self.traces[name] = self.waveform.plot(pen='c', width=3)
                self.waveform.setYRange(-0.05, 0.05, padding=0)
                #self.waveform.setXRange(0, self.CHUNK, padding=0.005)

            #if name == 'w_waveform':
            #    self.traces[name] = self.w_waveform.plot(pen='c', width=3)
            #    self.w_waveform.setYRange(-5e-5, 5e-5, padding=0.005)
            #    #self.w_waveform.setXRange(0, self.CHUNK, padding=0.005)

            if name == 'spectrum':
                self.traces[name] = self.spectrum.plot(pen='m', width=3)
                self.spectrum.setLogMode(x=True, y=True)
                self.spectrum.setYRange(np.log10(0.001), np.log10(20), padding=0)
                #self.spectrum.setXRange(np.log10(20), np.log10(self.RATE / 2), padding=0.005)

            #if name == 'out':
            #    self.traces[name] = self.out.plot(pen='c', width=3)
            #    self.out.setYRange(-0.02, 0.02, padding=0.05)
            #    #self.out.setXRange(0, self.CHUNK // 4, padding=0.005)

    def update_plots(self):

        previous_wf_data1 = self.wf_data[511:2048]
        previous_wf_data2 = self.wf_data[1023:2048]
        previous_wf_data3 = self.wf_data[1535:2048]

        # Get the data from the mic
        self.wf_data = self.stream.read(self.CHUNK, exception_on_overflow=False)

        # Unpack the data as ints
        self.wf_data = np.array(
            struct.unpack(str(self.CHUNK) + 'f',
                          self.wf_data))  # str(self.CHUNK) + 'h' denotes size and type of data

        # self.prova = np.append(self.prova, self.wf_data)

        # Aqui hem llegit un frame de 2048 samples provinent del micro, el plotegem
        self.set_plotdata(name='waveform', data_x=self.freqs, data_y=self.wf_data)

        # Li apliquem windowing i ho plotegem
        #self.set_plotdata(name='w_waveform', data_x=self.z, data_y=w(self.wf_data))

        # Apliquem la fft al windowed frame
        fft_signal = fft(w(self.wf_data))

        # Sine Analysis to get tfreq for the current frame
        sine_anal = sineAnal(fft_signal)  # li entra una fft de 1025 samples

        # Frequency scaling values
        ysfreq = sine_anal[0] * self.multiplicator  # scale of frequencies

        # Synthesis (with OverlapAdd and IFFT)
        fft_synth = sineSynth(sine_anal[1], ysfreq, sine_anal[2])  # retorna un frame de 1025 samples

        sp_data = np.abs(fft(self.wf_data))

        self.set_plotdata(name='spectrum', data_x=self.f, data_y=sp_data)

        if self.iterations != 0:
            # First auxiliary waveform
            wf_data1 = np.append(previous_wf_data1, self.wf_data[1:512])

            fft1 = fft(w(wf_data1))
            sine_anal1 = sineAnal(fft1)
            ysfreq1 = sine_anal1[0] * self.multiplicator
            fft_synth1 = sineSynth(sine_anal1[1], ysfreq1, sine_anal1[2])  # retorna un frame de 1025 samples

            out1 = overl(ifft(fft_synth1))  # Tenim un frame de 512 samples

            # Second auxiliary waveform
            wf_data2 = np.append(previous_wf_data2, self.wf_data[1:1024])

            fft2 = fft(w(wf_data2))
            sine_anal2 = sineAnal(fft2)
            ysfreq2 = sine_anal2[0] * self.multiplicator
            fft_synth2 = sineSynth(sine_anal2[1], ysfreq2, sine_anal2[2])  # retorna un frame de 1025 samples

            out2 = overl(ifft(fft_synth2))  # Tenim un frame de 512 samples

            # Third auxiliary waveform
            wf_data3 = np.append(previous_wf_data3, self.wf_data[1:1536])

            fft3 = fft(w(wf_data3))
            sine_anal3 = sineAnal(fft3)
            ysfreq3 = sine_anal3[0] * self.multiplicator
            fft_synth3 = sineSynth(sine_anal3[1], ysfreq3, sine_anal3[2])  # retorna un frame de 1025 samples

            out3 = overl(ifft(fft_synth3))  # Tenim un frame de 512 samples

            self.results = np.append(np.append(out1, out2), out3)
            self.result = np.append(self.result, self.results)

        out = overl(ifft(fft_synth))  # Tenim un frame de 512 samples

        #self.set_plotdata(name='out', data_x=self.j, data_y=out)

        # Save result and play it simultaneously
        self.result = np.append(self.result, out)

        if self.recording:
            self.result2 = self.result

        # We cut the signal to not lag the program with large arrays
        if len(self.result) >= 4097 and not self.recording:
            self.result = self.result[len(self.result) - 4096:]

        # If we are in the Real-Time Sine Transformations window and the listening checkbox is checked
        # we play the sound
        if self.listening and self.listen_checkbox.isChecked():
            sd.play(np.array(self.result[len(self.result) - 4096:]), fs)
        self.iterations = 1

    def animation(self):
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plots)
        self.timer.start(0)

    def saveResult(self):
        filename = 'output_rt_sinusoidal_' + str(self.recordings) + '.wav'
        awrite = es.MonoWriter(filename=filename, sampleRate=fs)
        awrite(self.result2)
        dialog = QMessageBox(self)
        dialog.setText('File saved as ' + filename)
        dialog.setWindowTitle('File saved!')
        dialog.setStyleSheet('color:white;')
        dialog.exec_()
