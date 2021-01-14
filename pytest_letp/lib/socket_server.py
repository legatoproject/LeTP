"""Network(Server) connection library."""
# pylint: skip-file
# Reenable pylint after error fixes.
import sys
import threading
import time
from pytest_letp.lib import swilog

if sys.version_info[0] > 2:
    import socketserver as SocketServer
else:
    import SocketServer

__copyright__ = "Copyright (C) Sierra Wireless Inc."


class ThreadedTCPRequestHandler(SocketServer.BaseRequestHandler):
    """The request handler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle method to implement communication to the client.
    """

    def setup(self):
        """Setup TCP server."""
        if not hasattr(self.server, "max_size"):
            swilog.warning(
                "[TCP SERVER] server.max_size not defined. Set it to default 128"
            )
            self.server.max_size = 10 * 1024
        if not hasattr(self.server, "responder"):
            swilog.warning(
                "[TCP SERVER] server.responder not defined. Set it to default True"
            )
            self.server.responder = True
        if not hasattr(self.server, "cur_data"):
            self.server.cur_data = b""
        if not hasattr(self.server, "wait_after_transaction"):
            self.server.wait_after_transaction = 5

    def handle(self):
        """Handle the TCP connection.

        Echo back data sent to server from client.
        """
        swilog.debug(
            "[TCP SERVER] Call TCP handle and wait for {} bytes".format(
                self.server.max_size
            )
        )
        # self.server.timeout is used to set the socket timeout
        timeout = self.server.timeout if self.server.timeout is not None else 15
        self.request.settimeout(timeout)
        while 1:
            try:
                self.data = self.request.recv(self.server.max_size).strip()
                if len(self.data) != 0:
                    swilog.debug(
                        "[TCP SERVER] {} received {} bytes:".format(
                            self.client_address[0], len(self.data)
                        )
                    )
                    swilog.debug(self.data)
                    if self.server.responder and len(self.data) != 0:
                        swilog.debug("[TCP SERVER] Send data")
                        self.request.sendall(self.data)
                    self.server.cur_data += self.data
                if self.server._BaseServer__shutdown_request or len(self.data) == 0:
                    break
            except Exception as e:
                # Usually due to timeout
                swilog.debug("[TCP SERVER] %s" % (e))
                if (
                    hasattr(self.server, "_BaseServer__shutdown_request")
                    and self.server._BaseServer__shutdown_request
                ):
                    break
        # Do not close the socket too early
        time.sleep(self.server.wait_after_transaction)


class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    """Threaded TCP server."""

    # Avoid [Errno 98] Address already in use
    allow_reuse_address = True


def get_tcp_server(ip, port, responder=True, max_size=128):
    """Get a TCP server.

    :param ip: ip address of the server
    :param port: tcp port
    :param responder: If True, send the received data back
    :param max_size: Max size read by the server for each request

    @returns the server instance

    @note Use serv.cur_data to get all the data received by the server
    """
    serv = ThreadedTCPServer((ip, port), ThreadedTCPRequestHandler)
    server_thread = threading.Thread(target=serv.serve_forever)
    # Exit the server thread when the main thread terminates
    server_thread.daemon = True
    server_thread.start()
    serv.max_size = max_size
    serv.responder = responder
    # Do not close the socket too early
    serv.wait_after_transaction = 5
    return serv


class ThreadedUDPRequestHandler(SocketServer.BaseRequestHandler):
    """The request handler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle method to implement communication to the client.
    """

    def setup(self):
        """Setup UDP server."""
        if not hasattr(self.server, "max_size"):
            swilog.warning(
                "[UDP SERVER] server.max_size not defined. Set it to default 128"
            )
            self.server.max_size = 10 * 1024
        if not hasattr(self.server, "responder"):
            swilog.warning(
                "[UDP SERVER] server.responder not defined. Set it to default True"
            )
            self.server.responder = True
        if not hasattr(self.server, "cur_data"):
            self.server.cur_data = b""
        if not hasattr(self.server, "wait_after_transaction"):
            self.server.wait_after_transaction = 5

    def handle(self):
        """Handle the UDP connection.

        Echo back data sent to server from client.
        """
        swilog.debug("[UDP SERVER] Call UDP handle")
        self.data = self.request[0].strip()
        socket = self.request[1]
        if self.server.responder and len(self.data) != 0:
            swilog.debug(
                "[UDP SERVER] {} received {} bytes:".format(
                    self.client_address[0], len(self.data)
                )
            )
            swilog.debug(self.data)
            swilog.debug("[UDP SERVER] Send data to %s" % self.client_address[0])
            socket.sendto(self.data, self.client_address)
        self.server.cur_data += self.data
        # Do not close the socket too early
        time.sleep(self.server.wait_after_transaction)


class ThreadedUDPServer(SocketServer.ThreadingMixIn, SocketServer.UDPServer):
    """Threaded UDP server."""

    allow_reuse_address = True


def get_udp_server(ip, port, responder=True, max_size=128):
    """Get an UDP server.

    :param ip: ip address of the server
    :param port: udp port
    :param responder: If True, send the received data back
    :param max_size: Max size read by the server for each request

    @Returns the server instance

    @note Use serv.cur_data to get all the data received by the server
    """
    serv = ThreadedUDPServer((ip, port), ThreadedUDPRequestHandler)
    server_thread = threading.Thread(target=serv.serve_forever)
    # Exit the server thread when the main thread terminates
    server_thread.daemon = True
    server_thread.start()
    serv.max_size = max_size
    serv.responder = responder
    # Do not close the socket too early
    serv.wait_after_transaction = 5
    return serv
