import socket
from qrcode import QRCode
from io import BytesIO
from tkinter import Tk, Label
from tkinter.ttk import Combobox
from PIL import Image, ImageTk


def show():
    addrs = socket.gethostbyname_ex(socket.gethostname())[2]

    #
    #
    # Tk

    font = (None, 12)

    root = Tk()
    root.title('Local IP Addr QR')
    root.geometry('400x400')
    root.minsize(400, 400)
    root.maxsize(400, 400)

    img_label = Label(root)
    img_label.pack(side='top', anchor='w', padx=10, pady=10)

    box = Combobox(root, values=addrs, state='readonly', font=font)
    box.pack(side='bottom', anchor='e', padx=10, pady=10)
    box.current(0)  # this will not trigger listener

    if len(addrs) == 1:
        label = Label(root, text='SINGLE', fg='green', font=font)
    else:
        label = Label(root, text='MULTI', fg='red', font=font)
    label.pack(side='bottom', anchor='e', padx=10)

    def listener(_):
        ip = 'Diabeat ' + box.get()  # prefix identifier

        buffer = BytesIO()

        qr = QRCode(border=0)
        qr.add_data(ip)
        qr.make()
        qr.make_image(back_color='transparent').save(buffer)

        img = Image.open(buffer).resize((300, 300))
        img = ImageTk.PhotoImage(img)

        img_label.config(image=img)
        img_label.img = img  # keep reference, prevent gc

    box.bind('<<ComboboxSelected>>', listener)
    listener(None)

    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass

    root.mainloop()


if __name__ == '__main__':
    show()
