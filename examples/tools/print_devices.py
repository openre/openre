# import PyOpenCL and Numpy. An OpenCL-enabled GPU is not required,
# OpenCL kernels can be compiled on most CPUs thanks to the Intel SDK for OpenCL
# or the AMD APP SDK.
import pyopencl as cl

def main():
    dev_type_str = {}
    for dev_type in ['ACCELERATOR', 'ALL', 'CPU', 'CUSTOM', 'DEFAULT', 'GPU']:
        dev_type_str[getattr(cl.device_type, dev_type)] = dev_type
    for platform_index, platform in enumerate(cl.get_platforms()):
        print 'ID: %s' % platform_index
        print platform.name
        print platform.profile
        print platform.vendor
        print platform.version
        for device in platform.get_devices():
            for param in ['NAME', 'BUILT_IN_KERNELS', 'MAX_COMPUTE_UNITS',
                          'GLOBAL_MEM_SIZE', 'MAX_MEM_ALLOC_SIZE', 'TYPE',
                          'MAX_WORK_GROUP_SIZE']:
                try:
                    value = device.get_info(getattr(cl.device_info, param))
                except (cl.LogicError, AttributeError):
                    continue
                print '\t',
                if param == 'TYPE':
                    value = '%s (%s)' % (
                        value,
                        dev_type_str.get(value, 'UNDEF')
                    )
                print '%s:\t%s' % (
                    param,
                    value
                )
        print ''
if __name__ == '__main__':
    main()
