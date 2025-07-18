import socket
from tkinter import Tk
from tkinter.ttk import Label, Combobox
import qrcode
from io import BytesIO
from PIL import Image, ImageTk

ips = socket.gethostbyname_ex(socket.gethostname())[2]

root = Tk()
root.title('t')

qrcode.make(ips[0]).save()
