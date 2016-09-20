import thread

servers = {}


def start(types=['http']):
    from .http import HttpServer

    global servers
    for type in types:
        if type not in servers:
            if type == 'http':
                server = HttpServer()
                thread.start_new_thread(server.start, ())
            servers[type] = server


def stop():
    for type, server in servers.iteritems():
        server.stop()
