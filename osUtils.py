from sys import platform

OSX = "osx"
LINUX = "linux"
WINDOWS = "windows"


def get_os():
    if platform == "linux" or platform == "linux2":
        return LINUX
    elif platform == "darwin":
        return OSX
    elif platform == "win32":
        return WINDOWS