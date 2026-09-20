"""Rounded native ttk buttons with hover, keyboard and focus states."""
import math
import tkinter as tk
from tkinter import ttk


class RoundedButton(ttk.Button):
    _serial = 0

    def __init__(self, parent, **kwargs):
        kwargs.pop('style', None)
        RoundedButton._serial += 1
        name = f'Round{RoundedButton._serial}'
        style = ttk.Style(parent)
        self._images = []
        for color in ('#32765A', '#265F48', '#204E3C', '#83988A', '#4B806F'):
            image = tk.PhotoImage(master=parent, width=40, height=40)
            radius = 13
            for y in range(40):
                distance = max(radius-y, y-(39-radius), 0)
                inset = int(math.ceil(radius-math.sqrt(max(0, radius*radius-distance*distance))))
                image.put(color, to=(inset, y, 40-inset, y+1))
            self._images.append(image)
        element = name + '.background'
        style.element_create(element, 'image', self._images[0],
                             ('disabled', self._images[3]), ('pressed', self._images[2]),
                             ('active', self._images[1]), ('focus', self._images[4]),
                             border=15, sticky='nsew')
        style.layout(name + '.TButton', [(element, {'sticky': 'nsew', 'children': [
            ('Button.padding', {'sticky': 'nsew', 'children': [('Button.label', {'sticky': 'nsew'})]})]})])
        style.configure(name + '.TButton', foreground='white', background=parent.cget('background'),
                        font=('Segoe UI', 11, 'bold'), padding=(18, 12), anchor='center')
        style.map(name + '.TButton', foreground=[('disabled', '#F0F3EF')])
        super().__init__(parent, style=name + '.TButton', takefocus=True, **kwargs)
