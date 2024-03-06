"""Provide basic URL functionalities."""
import os
import json
import socket
import requests
import swilog


def does_url_endswith(url, extension):
    """Check if the url path ends with a file extension."""
    if url:
        _, ext = os.path.splitext(url)
        return ext in extension

    return False


class Networker:
    """Provide basic URL operations."""

    def __init__(self, URL="http://get.central", auth=None):
        """Initialize all required parameters for Networker class."""
        self.URL = URL
        self.auth = auth

    def is_URL_reachable(self):
        """Return true if the URL is reachable; false otherwise."""
        req_obj = self.get()
        swilog.debug(
            f"Server returns: {req_obj.status_code} with the message: {req_obj.reason}"
        )
        return req_obj.status_code == 200

    def download(self, file_path, is_binary_file=True):
        """Download the URL's contents using the get request object."""
        try:
            os.remove(file_path)
        except:
            pass

        access = "w+"
        if is_binary_file:
            access = "wb+"

        req_obj = self.get()
        with open(file_path, access, encoding='UTF-8') as file_obj:
            file_obj.write(req_obj.content)

    def get(self, **extra_args):
        """Return the get request object."""
        req_obj = requests.get(self.URL, auth=self.auth, **extra_args)

        return req_obj

    def delete(self, **extra_args):
        """Return the delete request object."""
        req_obj = requests.delete(self.URL, auth=self.auth, **extra_args)

        return req_obj

    def post(self, data, **extra_args):
        """Perform post."""
        try:
            if isinstance(data, dict):
                r = requests.post(self.URL, data=data, **extra_args)
            else:
                r = requests.post(self.URL, json=json.loads(data), **extra_args)
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            print(err)
            return False
        return True

    def put(self, data, **extra_args):
        """Perform put."""
        try:
            json.loads(data)
        except json.decoder.JSONDecodeError:
            swilog.error(f"Invalid payload {data}")
            return False

        req_obj = requests.put(url=self.URL, data=data, auth=self.auth, **extra_args)

        return req_obj.status_code == 200

    def get_ip_from_url(self, port, ip_version="ipv4"):
        """Connect to url and retrieve IP address."""
        try:
            if ip_version == "ipv4":
                ip_addr = socket.getaddrinfo(self.URL, port, socket.AF_INET)[0][4][0]
                return ip_addr
            if ip_version == "ipv6":
                ip_addr = socket.getaddrinfo(self.URL, port, socket.AF_INET6)[0][4][0]
                return ip_addr
            else:
                print(f"IP version {ip_version} is not supported/found.")
                return None
        except:
            print("Could not reach URL and retrieve information.")
            return None
