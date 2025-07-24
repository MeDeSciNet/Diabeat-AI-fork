import socket
from io import BytesIO
from pathlib import Path
from tkinter import Tk, Label
from tkinter.ttk import Frame, Button, Combobox
from PIL import Image, ImageTk
from qrcode import QRCode, ERROR_CORRECT_H
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer


class App(Tk):

    @staticmethod
    def run():
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass
        finally:
            app = App()
            app.mainloop()

    def __init__(self):
        super().__init__()
        font = (None, 12)

        self.title('Addr QR')
        self.geometry('400x400')
        self.minsize(400, 400)
        self.maxsize(400, 400)

        #
        #
        # children

        self.image_label = Label(self)
        self.image_label.pack(side='top', anchor='nw', padx=10, pady=10)

        bottom_frame = Frame(self)
        bottom_frame.pack(side='bottom', fill='x', padx=10, pady=10)

        self.count_label = Label(self, font=font)
        self.count_label.pack(side='right', anchor='se', padx=10)

        self.combo_box = Combobox(bottom_frame, state='readonly', font=font)
        self.combo_box.pack(side='right')
        self.combo_box.bind('<<ComboboxSelected>>', self.set_qr_by_current)

        Button(
            bottom_frame,
            text='REFRESH',
            command=self.refresh
        ).pack(side='left')

        self.bind('<F5>', self.refresh)
        self.bind('<Control-r>', self.refresh)
        self.refresh()

    def refresh(self, event=None):
        addrs = socket.gethostbyname_ex(socket.gethostname())[2]
        if '127.0.0.1' in addrs:
            addrs.remove('127.0.0.1')
        self.combo_box.config(values=addrs)

        count = len(addrs)

        if count == 0:
            self.combo_box.set('')
            self.count_label.config(text='NONE', fg='black')
            self.image_label.config(image=None)
            self.image_label.image = None
        elif count == 1:
            self.combo_box.current(0)
            self.count_label.config(text='SINGLE', fg='green')
            self.set_qr_by_current()
        else:
            self.combo_box.current(0)
            self.count_label.config(text='MULTI', fg='red')
            self.set_qr_by_current()

    def set_qr_by_current(self, event=None):
        data = 'Diabeat ' + self.combo_box.get()  # prefix identifier
        buffer = BytesIO()

        qr = QRCode(error_correction=ERROR_CORRECT_H, border=0)
        qr.add_data(data)
        qr.make()
        qr.make_image(
            image_factory=StyledPilImage,
            module_drawer=RoundedModuleDrawer(),
            back_color='transparent',
            embeded_image_path=Path(__file__).parent / 'icon.avif'
        ).save(buffer)

        image = Image.open(buffer).resize((300, 300))
        image = ImageTk.PhotoImage(image)

        self.image_label.config(image=image)
        self.image_label.image = image  # keep reference, prevent gc


if __name__ == '__main__':
    App.run()
