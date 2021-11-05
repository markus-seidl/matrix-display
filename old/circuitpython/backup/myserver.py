import io
import gc
from micropython import const
# from adafruit_requests import parse_headers
import adafruit_esp32spi.adafruit_esp32spi_socket as socket

_the_interface = None  # pylint: disable=invalid-name


def set_interface(iface):
    """Helper to set the global internet interface"""
    global _the_interface  # pylint: disable=global-statement, invalid-name
    _the_interface = iface
    socket.set_interface(iface)


NO_SOCK_AVAIL = const(255)


def custom_parse_headers(sock):
    """
      This will only deliver the contents of 'content-length' and discard anything else

      Parses the header portion of an HTTP request/response from the socket.
      Expects first line of HTTP request/response to have been read already

      return: header dictionary
      rtype: content-length
     """
    content_length = None
    found = False
    while True:
        line = sock.readline()
        if not line or line == b"\r\n":
            break

        if found:
            continue

        # print("**line: ", line)
        title, content = line.split(b': ', 1)
        if title and content:
            title = str(title.lower(), 'utf-8')
            if title == 'content-length':
                content_length = int(str(content, 'utf-8'))
                found = True
    return content_length


class MyStreamingServer:
    def __init__(self, port=80, debug=False, application=None):
        self.application = application
        self.port = port
        self._server_sock = socket.socket(socknum=NO_SOCK_AVAIL)
        self._client_sock = socket.socket(socknum=NO_SOCK_AVAIL)
        self._debug = debug

        self._response_status = None
        self._response_headers = []

    def start(self):
        """
        starts the server and begins listening for incoming connections.
        Call update_poll in the main loop for the application callable to be
        invoked on receiving an incoming request.
        """
        self._server_sock = socket.socket()
        _the_interface.start_server(self.port, self._server_sock.socknum)
        if self._debug:
            ip = _the_interface.pretty_ip(_the_interface.ip_address)
            print("Server available at {0}:{1}".format(ip, self.port))
            print(
                "Sever status: ",
                _the_interface.get_server_state(self._server_sock.socknum),
            )

    def update_poll(self):
        """
        Call this method inside your main event loop to get the server
        check for new incoming client requests. When a request comes in,
        the application callable will be invoked.
        """
        self.client_available()
        if self._client_sock and self._client_sock.available():
            environ = self._get_environ(self._client_sock)
            result = self.application(environ, self._start_response)
            self.finish_response(result)

    def finish_response(self, result):
        """
        Called after the application callbile returns result data to respond with.
        Creates the HTTP Response payload from the response_headers and results data,
        and sends it back to client.
        :param string result: the data string to send back in the response to the client.
        """
        try:
            response = "HTTP/1.1 {0}\r\n".format(self._response_status)
            for header in self._response_headers:
                response += "{0}: {1}\r\n".format(*header)
            response += "\r\n"
            self._client_sock.send(response.encode("utf-8"))
            for data in result:
                if isinstance(data, bytes):
                    self._client_sock.send(data)
                else:
                    self._client_sock.send(data.encode("utf-8"))
            gc.collect()
        finally:
            if self._debug:
                print("closing")
            self._client_sock.close()

    def client_available(self):
        """
        returns a client socket connection if available.
        Otherwise, returns None
        :return: the client
        :rtype: Socket
        """
        sock = None
        if self._server_sock.socknum != NO_SOCK_AVAIL:
            if self._client_sock.socknum != NO_SOCK_AVAIL:
                # check previous received client socket
                if self._debug > 2:
                    print("checking if last client sock still valid")
                if self._client_sock.connected() and self._client_sock.available():
                    sock = self._client_sock
            if not sock:
                # check for new client sock
                if self._debug > 2:
                    print("checking for new client sock")
                client_sock_num = _the_interface.socket_available(
                    self._server_sock.socknum
                )
                sock = socket.socket(socknum=client_sock_num)
        else:
            print("Server has not been started, cannot check for clients!")

        if sock and sock.socknum != NO_SOCK_AVAIL:
            if self._debug > 2:
                print("client sock num is: ", sock.socknum)
            self._client_sock = sock
            return self._client_sock

        return None

    def _start_response(self, status, response_headers):
        """
        The application callable will be given this method as the second param
        This is to be called before the application callable returns, to signify
        the response can be started with the given status and headers.
        :param string status: a status string including the code and reason. ex: "200 OK"
        :param list response_headers: a list of tuples to represent the headers.
            ex ("header-name", "header value")
        """
        self._response_status = status
        self._response_headers = [("Server", "esp32WSGIServer")] + response_headers

    def _get_environ(self, client):
        """
        The application callable will be given the resulting environ dictionary.
        It contains metadata about the incoming request and the request body ("wsgi.input")
        :param Socket client: socket to read the request from
        """
        env = {}
        line = str(client.readline(), "utf-8")
        (method, path, ver) = line.rstrip("\r\n").split(None, 2)

        env["REQUEST_METHOD"] = method
        if path.find("?") >= 0:
            env["PATH_INFO"] = path.split("?")[0]
            env["QUERY_STRING"] = path.split("?")[1]
        else:
            env["PATH_INFO"] = path

        content_length = custom_parse_headers(client)
        if content_length:
            env['content-length'] = content_length
            env["wsgi.input"] = client
        else:
            env['content-length'] = -1
            env["wsgi.input"] = None

        return env
