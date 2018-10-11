
from tkinter import *
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import bgs

class FonToolsGUI(tk.Frame):
    def __init__(self,master=None):
      tk.Frame.__init__(self,master)
      self.master.title("FON Tools")

      self.windows = []
      self.open_close_btn_text = tk.StringVar()
      self.open_close_btn_text.set("Abrir FON Tools")
      self.open_close_btn = tk.Button(self,textvariable=self.open_close_btn_text,command=self.toggle_window)
      self.open_close_btn.pack()
      self.app_opened = False
      conn = bgs.get_db_connection()
      print(bgs.get_next_target(conn,"Naunin", "Belanit"))
      conn.close()
      
      nb = ttk.Notebook(self.master)
      page1 = ttk.Frame(nb)
      page2 = ttk.Frame(nb)
      text = ScrolledText(page2)
      text.pack(expand=1, fill="both")
      nb.add(page1, text='One')
      nb.add(page2, text='Two')
      nb.pack(expand=1, fill="both")

      self.packetlistframe = ttk.PanedWindow(page1)
      self.packetlistframe.treeview = ttk.Treeview(self.packetlistframe,columns=("Timestamp","ServerID","PackageID","PackageSize","PackageData"))
      self.packetlistframe.treeview.heading("#0",text="#")
      self.packetlistframe.treeview.column("#0",width=60,stretch=NO,anchor=CENTER)
      self.packetlistframe.treeview.heading("Timestamp",text="Timestamp",anchor=CENTER)
      self.packetlistframe.treeview.column("Timestamp",width=140,stretch=NO,anchor=CENTER)
      self.packetlistframe.treeview.heading("ServerID",text="Srv ID",anchor=CENTER)
      self.packetlistframe.treeview.column("ServerID",width=50,stretch=NO,anchor=CENTER)
      self.packetlistframe.treeview.heading("PackageID",text="Pck ID",anchor=CENTER)
      self.packetlistframe.treeview.column("PackageID",width=50,stretch=NO,anchor=CENTER)
      self.packetlistframe.treeview.heading("PackageSize",text="Size",anchor=CENTER)
      self.packetlistframe.treeview.column("PackageSize",width=40,stretch=NO,anchor=CENTER)
      self.packetlistframe.treeview.heading("PackageData",text="Data",anchor=CENTER)
      self.packetlistframe.treeview.pack(expand=True, fill='both')
      self.packetlistframe.treeview.bind('<<TreeviewSelect>>',self.selectItemCallback)
      self.packetlistframe.pack(expand=True, fill='both',side=RIGHT)

    def selectItemCallback(self,event):
      pass
    def toggle_window(self):
      self.app_opened = not self.app_opened
      if self.app_opened:
        self.new_window()
        self.open_close_btn_text.set("Cerrar FON Tools")
      else:
        self.del_window()
        self.open_close_btn_text.set("Abrir FON Tools")
      
    def new_window(self,event=None):
        new = tk.Toplevel(self,width=800,height=600)
        new.title("FON Tools")
        self.windows.append(new)

    def del_window(self,event=None):
        self.windows.pop().destroy()
        
app = FonToolsGUI()

app.mainloop()