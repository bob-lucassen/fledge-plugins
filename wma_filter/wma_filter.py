# -*- coding: utf-8 -*-

# Fledge_BEGIN
# See: http://fledge-iot.readthedocs.io/
# Fledge_END

""" Module for WMA filter plugin

Generate Windowed Moving Average
"""

import time
import copy
import logging

import numpy as np

from fledge.common import logger
import filter_ingest

__author__ = "Marc van Raalte"
__copyright__ = "Copyright (c) 2022 System Operations"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_LOGGER = logger.setup(__name__, level = logging.WARN)

_DEFAULT_CONFIG = {
    'plugin': {
        'description': 'Windowed Moving Average filter plugin',
        'type': 'string',
        'default': 'wma_filter',
        'readonly': 'true'
    },
    'enable': {
        'description': 'Enable wma plugin',
        'type': 'boolean',
        'default': 'false',
        'displayName': 'Enabled',
        'order': "3"
    },
    'filter_time': {
        'description': 'Interval time of the wma in seconds',
        'type': 'integer',
        'default': '10',
        'displayName': 'Filter time in seconds',
        'order': "2"
    },
    'datapoint': {
        'description': 'Datapoint name for calculated wma value',
        'type': 'string',
        'default': 'wma_filter',
        'displayName': 'WMA datapoint',
        'order': "1"
    }
}


def plugin_info():
    """ Returns information about the plugin
    Args:
    Returns:
        dict: plugin information
    Raises:
    """
    return {
        'name': 'wma_filter',
        'version': '1.0.0',
        'mode': "none",
        'type': 'filter',
        'interface': '1.0',
        'config': _DEFAULT_CONFIG
    }


def plugin_init(config, ingest_ref, callback):
    """ Initialise the plugin
    Args:
        config: JSON configuration document for the Filter plugin configuration category
        ingest_ref:
        callback:
    Returns:
        data: JSON object to be used in future calls to the plugin
    Raises:
    """
    handle = copy.deepcopy(config)

    handle['the_callback'] = callback
    handle['the_ingest_ref'] = ingest_ref
    # plugin shutdown indicator
    handle['shutdown_in_progress'] = False
    # datapoint name
    handle['datapoint'] = config['datapoint']['value']  

    _LOGGER.debug("plugin_init for filter WMA called")
    
    # window size
    wsize = int(config['filter_time']['value'])
    handle['wsize'] = wsize
    # wma
    handle['xmean'] = 0
    # window
    handle['window'] = np.zeros(wsize)
    # counter 
    handle['counter'] = 0
    
    return handle


def compute_wma(handle, reading):
    """ Compute WMA

    Args:
        A reading data
    """
    
    wsize = handle['wsize']
    xmean = handle['xmean']
    window = handle['window']
    
    for attribute in list(reading):
        elem = reading[attribute]      
        xlast = window[wsize-1]      
        frame = window[0:wsize-1]
        window[1:]=frame
        window[0] = elem
        xfirst = window[0]
        xsum = wsize*xmean + xfirst - xlast
        xmean = xsum/wsize
        handle['counter'] = handle['counter'] + 1
        reading[handle['datapoint']] = xmean
        handle['xmean'] = xmean
        handle['window'] = window
        #wma = np.mean(window)
        #reading[datapoint] = wma



def plugin_reconfigure(handle, new_config):
    """ Reconfigures the plugin

    Args:
        handle: handle returned by the plugin initialisation call
        new_config: JSON object representing the new configuration category for the category
    Returns:
        new_handle: new handle to be used in the future calls
    """
    
    _LOGGER.debug("Old config for wma plugin {} \n new config {}".format(handle, new_config))
    new_handle = copy.deepcopy(new_config)
     
    _LOGGER.debug("plugin_init for filter WMA called")
    
    new_handle['datapoint'] = new_config['datapoint']['value']
    
    wsize = int(new_config['filter_time']['value'])
    new_handle['wsize'] = wsize
    # wma
    new_handle['xmean'] = 0
    # window
    new_handle['window'] = np.zeros(wsize)
    # counter 
    new_handle['counter'] = 0
    
    return new_handle


def plugin_shutdown(handle):
    """ Shutdowns the plugin doing required cleanup.

    Args:
        handle: handle returned by the plugin initialisation call
    Returns:
        plugin shutdown
    """
    handle['shutdown_in_progress'] = True
    time.sleep(1)
   
    _LOGGER.info('filter ema plugin shutdown.')


def plugin_ingest(handle, data):
    """ Modify readings data and pass it onward

    Args:
        handle: handle returned by the plugin initialisation call
        data: readings data
    """
    
    if handle['shutdown_in_progress']:
        return

    if handle['enable']['value'] == 'false':
        # Filter not enabled, just pass data onwards
        filter_ingest.filter_ingest_callback(handle['the_callback'], handle['the_ingest_ref'], data)
        return

    # Filter is enabled: compute WMA for each reading
    for elem in data:
        compute_wma(handle, elem['readings'])

    # Pass data onwards
    if handle['counter'] > handle['wsize'] -1:
    	filter_ingest.filter_ingest_callback(handle['the_callback'], handle['the_ingest_ref'], data)
    	handle['counter'] = 0

    _LOGGER.debug("wma filter_ingest done")
