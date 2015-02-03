#!/usr/bin/env python
# coding: utf-8
# Copyright 2013 Abram Hindle
# Modified by Kyle Richelhoff, 2014.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Do not use urllib's HTTP GET and POST mechanisms.
# Write your own HTTP GET and POST
# The point is to understand what you have to send and get experience with it

import sys
import socket
import re
# you may use urllib to encode data appropriately
import urllib

# Use this to parse the domain.
# This is in utilibs in Python 3.
from urlparse import urlparse


def help():
    """CLI help line printed if no arguments specified."""
    print "httpclient.py [GET/POST] [URL]\n"


class HTTPRequest(object):
    """The request object we pass back to the developer."""
    def __init__(self, code=200, body=""):
        self.code = code
        self.body = body


class HTTPClient(object):
    """Basic HTTP Client to interface with."""
    def __init__(self):

        # Response headers from the request
        self.headers = {}

        # Protocol returned and status of the request
        self.protocol_returned = None
        self.response_code = None
        self.body = None

        # Other response data
        self.port = None
        self.host = None
        self.path = None
        self.user_agent = "PracticeHTTPClient/1.1 python/sockets"

    def connect(self, host, port):
        """Use sockets to connect to the HTTP service."""

        # 30 seconds timeout. HTTP was too slow.
        timeout = 30

        # Create a socket connection to the TCP service
        print "CONNECTING TO: {} on port {}.".format(host, port)
        sock = socket.create_connection((host, port), timeout=timeout)

        return sock

    # All of these had the data parameter removed.
    # get_code, get_headers, get_body.

    def get_code(self):
        """Return the status code. ie. 200"""
        return self.response_code

    def get_headers(self):
        """Returns dictionary of headers."""
        return self.headers

    def get_body(self):
        """Return the body of the response."""
        return self.body

    def recvall(self, sock):
        """Return the buffer from the socket, wait until complete."""
        buffer = bytearray()
        done = False
        while not done:
            part = sock.recv(1024)
            if part:
                buffer.extend(part)
            else:
                done = not part
        return str(buffer)

    def parse_url(self, url):
        """We need to break-up the URL into two segments, host and path. RFC 1808.
        Parameters:
            url -> http://google.ca/404

        Returns: Host, Port(default:80), Path
        """
        # Default port is 80 if none is found
        port = 80
        port_given = None
        url_given = None

        # Parse url from utilibs.
        parse_object = urlparse(url)

        # url_parse finds the port if provided, if not then netloc is the full host.
        # This will only work for IPv4.
        if parse_object.netloc.find(":") > 0:
            url_given, port_given = parse_object.netloc.split(":")

        # Host, port, path
        return url_given or parse_object.netloc, port_given or port, parse_object.path

    def parse_response(self, response):
        """Parse the raw data returned by the server to the socket.
        Parameters:
            response -> A string of response headers and body.

        Returns: Host, Port(default:80), Path
        """

        # Split the headers into an array by each line
        headers_split = response.split('\r\n')

        # The first line is separated by spaces.
        # We only care about the status and not anything after.
        # ie. HTTP/1.1 200 OK
        first_line_response = headers_split[0].split(" ")

        self.protocol_returned = first_line_response[0]
        self.response_code = int(first_line_response[1])

        # We need to remove the first line
        # because parsing it can be problematic.
        headers_split.pop(0)

        # This is to index each request with its data into a dictionary object.
        # ie. Connection: keep-alive
        # In no way is this meant to be optimal, only ease of access.
        headers_index = 0
        for header in headers_split:

            # If the header exists and isn't a blank line.
            if header:
                self.headers[header[:header.index(" ")].strip(":")] = header[header.index(" ") + 1:]
                headers_index += 1
            else:
                # We are at the body of the request, break off.
                break

        # Everything after the index is the body
        # of the request in the HTTP response.
        # We can now join the body back together by \n
        self.body = "\n".join(headers_split[headers_index+1:])

    def send_headers(self, method, sock, args=None):
        """Send the headers AND body if supplied.
        Parameters:
            method -> A string of the HTTP/1.1 method to use.
            sock -> A socket object that has been opened.
            args(optional) -> A dictionary to url encode in the body
                of the request.

        Returns: None
        """
        body = ""
        if method not in ["GET", "POST"]:
            # Method not supported
            raise NotImplementedError("Method: {} is not supported".format(method))

        # START Headers
        sock.sendall("{} {} HTTP/1.1\r\n".format(method, self.path))
        sock.sendall("Host: {}\r\n".format(self.host))
        sock.sendall("User-Agent: {}\r\n".format(self.user_agent))
        sock.sendall("Accept: */*\r\n")
        sock.sendall("Connection: close\r\n")

        # If there is a body, we need to send that as well.
        if args:
            try:
                body = urllib.urlencode(args)
            except:
                body = ""
            sock.sendall("Content-Type: application/x-www-form-urlencoded\r\n")
            sock.sendall("Content-Length: {}\r\n".format(len(body)))

        # END Headers
        sock.sendall("\r\n")

        # Body if one was supplied.
        if args:
            sock.sendall(body)

    def GET(self, url, args=None, printable=False):
        """Basic GET request.
        Parameters:
            url -> A string of the resource. ie. http://google.ca/hello_world
            args(optional) -> A dictionary to url encode in the body
                of the request.

        Returns: HTTPRequest Object
        """
        # Parse the URL provided.
        self.host, self.port, self.path = self.parse_url(url)

        # Connect to the HTTP service.
        sock = self.connect(self.host, self.port)

        # Send header information.
        self.send_headers("GET", sock, args)

        # Receive everything from the socket
        response = self.recvall(sock)

        # User needs to see in stdout
        if printable:
            print response

        # Make sure the socket is closed.
        sock.close()

        # Parse response.
        self.parse_response(response)

        return HTTPRequest(self.response_code, self.body)

    def POST(self, url, args=None, printable=False):
        """Basic POST request.
        Parameters:
            url -> A string of the resource. ie. http://google.ca/hello_world
            args(optional) -> A dictionary to url encode in the body
                of the request.

        Returns: HTTPRequest Object
        """
        # Parse the URL provided.
        self.host, self.port, self.path = self.parse_url(url)

        # Connect to the HTTP service.
        sock = self.connect(self.host, self.port)

        # Send header information.
        self.send_headers("POST", sock, args)

        # Receive everything from the socket
        response = self.recvall(sock)

        # User needs to see in stdout
        if printable:
            print response

        # Make sure the socket is closed.
        sock.close()

        # Parse response.
        self.parse_response(response)

        return HTTPRequest(self.response_code, self.body)

    def command(self, url, command="GET", args=None):
        # Additional args as required after the {GET/POST URL}
        if command == "POST":
            return self.POST(url, args, printable=True)
        else:
            return self.GET(url, args, printable=True)

if __name__ == "__main__":
    client = HTTPClient()

    # Default command is assumed to be a GET request
    command = "GET"

    # No arguments provided then show help.
    if len(sys.argv) <= 1:
        help()
        sys.exit(1)

    # Else if specified: {python httpclient.py GET/POST URL}
    elif len(sys.argv) == 3:
        print client.command(sys.argv[2], sys.argv[1])

    # Default GET request fallback.
    else:
        print client.command(sys.argv[1], command)
