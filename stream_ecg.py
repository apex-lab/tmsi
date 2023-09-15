from PySide2.QtWidgets import *
import sys
from os.path import join, dirname, realpath
this_dir = dirname(realpath(__file__)) # directory of this file
tmsi_dir = join(this_dir, 'tmsi-python-interface')
sys.path.append(tmsi_dir)
from TMSiSDK.tmsi_sdk import TMSiSDK, DeviceType, DeviceInterfaceType, DeviceState
from TMSiSDK.tmsi_errors.error import TMSiError, TMSiErrorCode, DeviceErrorLookupTable
from TMSiFileFormats.file_writer import FileWriter, FileFormat
from TMSiSDK.device import ChannelType
from TMSiGui.gui import Gui
from TMSiPlotterHelpers.signal_plotter_helper import SignalPlotterHelper
from TMSiSDK.device.devices.saga.saga_API_enums import SagaBaseSampleRate

AUX_CHANS = []
BIP_CHANS = [0] # bipolar channels for ECG

try:
    # Execute a device discovery. This returns a list of device-objects for every discovered device.
    print('Looking for devices...')
    TMSiSDK().discover(
        dev_type = DeviceType.saga, 
        dr_interface = DeviceInterfaceType.wifi, 
        ds_interface = DeviceInterfaceType.usb
        )
    discoveryList = TMSiSDK().get_device_list(DeviceType.saga)

    if (len(discoveryList) > 0):

        # Get the handle to the first discovered device.
        dev = discoveryList[0]
        
        # Open a connection to the SAGA-system
        dev.open()
        print('Device opened.')

        # set the sampling rate as close as we can to desired 
        print('Setting the sample rate...')
        dev.set_device_sampling_config(
            base_sample_rate = SagaBaseSampleRate.Decimal,
            channel_type = ChannelType.all_types, 
            channel_divider = 8 # this is minimum srate of 500 Hz
            )
        fs_info = dev.get_device_sampling_frequency(detailed = True)
        print('\n\nThe updated base-sample-rate is {0} Hz.'.format(fs_info['base_sampling_rate']))
        print('\nThe updated sample-rates per channel-type-group are :')
        for fs in fs_info:
            if fs != 'base_sampling_rate':
                print('{0} = {1} Hz'.format(fs, fs_info[fs]))

        # disable all but specified AUX and BIP channels
        ch_list = dev.get_device_channels()
        AUX_count = 0
        BIP_count = 0
        enable_channels = []
        disable_channels = []
        for idx, ch in enumerate(ch_list):
            if (ch.get_channel_type() == ChannelType.AUX):
                if AUX_count in AUX_CHANS:
                    enable_channels.append(idx)
                else:
                    disable_channels.append(idx)
                AUX_count += 1
            elif (ch.get_channel_type()== ChannelType.BIP):
                if BIP_count in BIP_CHANS:
                    enable_channels.append(idx)
                else:
                    disable_channels.append(idx)
                BIP_count += 1
            else :
                disable_channels.append(idx)
        dev.set_device_active_channels(enable_channels, True)
        dev.set_device_active_channels(disable_channels, False)
           
        # Initialise the lsl-stream
        stream = FileWriter(FileFormat.lsl, 'SAGA')
        
        # Pass the device information to the LSL stream.
        stream.open(dev)
        print('Opened LSL stream.')
    
        # Check if there is already a plotter application in existence
        app = QApplication.instance()
        
        # Initialise the plotter application if there is no other plotter application
        if not app:
            app = QApplication(sys.argv)
            
        plotter_helper = SignalPlotterHelper(device=dev)
        # Define the GUI object and show it 
        gui = Gui(plotter_helper = plotter_helper)
         # Enter the event loop
        app.exec_()
        
        # Close the file writer after GUI termination
        stream.close()
        
        # Close the connection to the SAGA device
        dev.close()
    
except TMSiError as e:
    print(e)
    
        
finally:
    if 'dev' in locals():
        # Close the connection to the device when the device is opened
        if dev.get_device_state() == DeviceState.connected:
            dev.close()
