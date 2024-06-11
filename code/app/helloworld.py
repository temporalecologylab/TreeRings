import tkinter as tk

window = tk.Tk()
window.title("Hello World")


def handle_button_press(event):
    window.destroy()


button = tk.Button(text="hello WORLD!")
button.bind("<Return>", handle_button_press)
button.pack()

# Start the event loop.
window.mainloop()

