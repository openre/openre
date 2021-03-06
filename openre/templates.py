# -*- coding: utf-8 -*-
"""
Jinja2 templates
"""
import numpy as np
from jinja2 import Environment, PackageLoader, ChoiceLoader

TEMPLATES_LOCATIONS = set()

def create_env(package_name=None):
    if package_name is None:
        package_name = list(TEMPLATES_LOCATIONS)
    if isinstance(package_name, set):
        package_name = list(package_name)
    if isinstance(package_name, basestring):
        package_name = [package_name]
    env = Environment(
        loader=ChoiceLoader([
            PackageLoader(name, 'templates') for name in package_name
        ])
    )
    env.filters['to_c_type'] = to_c_type
    return env

def to_c_type(np_type):
    """
    Convert numpy data type to C data type (for OpenCL devices).
    See:
        NumPy data types:
        http://docs.scipy.org/doc/numpy/user/basics.types.html
        OpenCL data types:
        https://www.khronos.org/registry/cl/sdk/1.2/docs/man/xhtml/scalarDataTypes.html
    """
    if isinstance(np_type, basestring):
        np_type = getattr(np, np_type)
    # Byte (-128 to 127)
    if np_type == np.int8:
        return 'char'
    #Integer (-32768 to 32767)
    if np_type == np.int16:
        return 'short'
    #Integer (-2147483648 to 2147483647)
    if np_type == np.int32:
        return 'int'
    #Integer (-9223372036854775808 to 9223372036854775807)
    if np_type == np.int64:
        return 'long'
    #Unsigned integer (0 to 255)
    if np_type == np.uint8:
        return 'unsigned char'
    #Unsigned integer (0 to 65535)
    if np_type == np.uint16:
        return 'unsigned short'
    #Unsigned integer (0 to 4294967295)
    if np_type == np.uint32:
        return 'unsigned int'
    #Unsigned integer (0 to 18446744073709551615)
    if np_type == np.uint64:
        return 'unsigned long'
    #Half precision float: sign bit, 5 bits exponent, 10 bits mantissa
    if np_type == np.float16:
        return 'half'
    #Single precision float: sign bit, 8 bits exponent, 23 bits mantissa
    if np_type == np.float32:
        return 'float'
    #Double precision float: sign bit, 11 bits exponent, 52 bits mantissa
    if np_type == np.float64:
        return 'double'

