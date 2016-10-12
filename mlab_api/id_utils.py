'''
Helpers to get IDs properly marshaled
'''


def location_id(d):
    '''
    Create ID for locations
    '''
    print('got d =', d)
    if 'location_key' in d:
        return d['location_key']
    if 'client_location_key' in d:
        return d['client_location_key']
    if 'child_location_key' in d:
        return d['child_location_key']
    if 'id' in d:
        return d['id']

    return None


def client_id(d):
    '''
    Create ID for clients
    '''
    return d['client_asn_number']

def server_id(d):
    '''
    Create ID for servers
    '''
    return d['server_asn_number']


def location_client_id(d):
    '''
    Create composite ID for locations + clients
    '''
    return '%s_%s' % (location_id(d), client_id(d))


def location_server_id(d):
    '''
    Create composite ID for locations + servers
    '''
    return '%s_%s' % (location_id(d), server_id(d))

def location_client_server_id(d):
    '''
    Create composite ID for locations + clients + servers
    '''
    return '%s_%s_%s' % (location_id(d), client_id(d), server_id(d))

def client_server_id(d):
    '''
    Create composite ID for clients + servers
    '''
    return '%s_%s' % (client_id(d), server_id(d))
