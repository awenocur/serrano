VERSION = (2, 0, 1, 'final')

def get_version():
    version = '%s.%s' % VERSION[:2]
    if version[2]:
        version = '%s.%s' % (version, VERSION[2])

    if len(VERSION) > 3:
        if VERSION[3:] == ('alpha', 0):
            version = '%spre-alpha' % version
        else:
            if VERSION[3] != 'final':
                version = '%s%s%s' % (version, VERSION[3], VERSION[4])
    return version
