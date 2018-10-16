
try:
  from tkinter import *
  import tkinter as tk
  from tkinter import ttk
except:
  from Tkinter import *
  import ttk
  import Tkinter as tk

import bgs


class FonToolsGUI(tk.Toplevel):
    def __init__(self,master=None):
      tk.Toplevel.__init__(self,master)
      self.title("FON Tools")
      
      nb = ttk.Notebook(self)
      pageConfiguration = ttk.Frame(nb)
      pageOverview = ttk.Frame(nb)
      pageExpansions = ttk.Frame(nb)
      pageRetreats = ttk.Frame(nb)
      pageWars = ttk.Frame(nb)
      pageUABombing = ttk.Frame(nb)
      nb.add(pageConfiguration, text='Configuration')
      nb.add(pageOverview, text='Overview')
      nb.add(pageExpansions, text='Expansions')
      nb.add(pageRetreats, text='Retreats')
      nb.add(pageWars, text='Wars')
      nb.add(pageUABombing, text='UA-Bombing')
      nb.pack(expand=1, fill="both")
      
      self.configuration_frame = ttk.PanedWindow(pageConfiguration)
      self.configuration_frame.updatedb_btn = ttk.Button(self.configuration_frame,text="Update Database",command=self.update_tick)
      self.configuration_frame.updatedb_btn.pack()
      self.configuration_frame.pack(expand=True, fill='both',side=LEFT)
      self.overview_frame = ttk.PanedWindow(pageOverview)
      self.overview_frame.combo = ttk.Combobox(self.overview_frame)
      self.overview_frame.combo.pack(side=TOP)
      self.overview_frame.combo.bind("<<ComboboxSelected>>", self.overview_selection_changed)
      self.overview_frame.treeview = ttk.Treeview(self.overview_frame,columns=("Faction","Influence","State","Pending","Recovering","Player","Last Update"))
      self.overview_frame.treeview.heading("#0",text="#")
      self.overview_frame.treeview.column("#0",width=30,stretch=NO,anchor=CENTER)
      self.overview_frame.treeview.heading("Faction",text="Faction",anchor=CENTER)
      self.overview_frame.treeview.column("Faction",width=240,stretch=NO,anchor="w")
      self.overview_frame.treeview.heading("Influence",text="Influence",anchor=CENTER)
      self.overview_frame.treeview.column("Influence",width=50,stretch=NO,anchor=CENTER)
      self.overview_frame.treeview.heading("State",text="State",anchor=CENTER)
      self.overview_frame.treeview.column("State",width=150,stretch=NO,anchor=CENTER)
      self.overview_frame.treeview.heading("Pending",text="Pending",anchor=CENTER)
      self.overview_frame.treeview.column("Pending",width=240,stretch=NO,anchor=CENTER)
      self.overview_frame.treeview.heading("Recovering",text="Recovering",anchor=CENTER)
      self.overview_frame.treeview.column("Recovering",width=240,stretch=NO,anchor=CENTER)
      self.overview_frame.treeview.heading("Player",text="Player",anchor=CENTER)
      self.overview_frame.treeview.column("Player",width=140,stretch=NO,anchor=CENTER)
      self.overview_frame.treeview.heading("Last Update",text="Last Update",anchor=CENTER)
      self.overview_frame.treeview.column("Last Update",width=140,stretch=NO,anchor=CENTER)
      self.overview_frame.treeview.pack(expand=True, fill='both')
      self.overview_frame.treeview.bind('<<TreeviewSelect>>',self.selectItemCallback)
      self.overview_frame.pack(expand=True, fill='both',side=RIGHT)
      self.overview_frame.combo["values"] = ["Naunin", "HR 6177", "Ratemere", "Maopi", "Smethells 1"]
      self.conn = bgs.get_db_connection()
      
      
    def update_tick(self):
      bgs.update_tick(self.conn)
      
    def selectItemCallback(self,event):
      pass
    
    def overview_selection_changed(self,event):
      system_name = self.overview_frame.combo.get()
      self.update_overview_frame(system_name)
    
    def update_overview_frame(self,system_name):
      self.overview_frame.treeview.delete(*self.overview_frame.treeview.get_children())
      i=0
      star_system = bgs.System(self.conn,system_name)
      if star_system:
        system_factions = star_system.get_current_factions(self.conn)
        for faction in system_factions:
          f = bgs.Faction(self.conn,faction)
          influence = f.get_current_influence_in_system(self.conn, system_name)
          active_state = f.get_states(self.conn,'activeState')[0][2]
          pending_states = ", ".join([state[2] for state in f.get_states(self.conn,'pendingState')])
          recovering_states = ", ".join([state[2] for state in f.get_states(self.conn,'recoveringState')])
          item = self.overview_frame.treeview.insert("", END, text=str(i), values=(f.name,influence*100.0,active_state,pending_states,recovering_states, "YES" if f.is_player else "NO",""))
          i=i+1

class FonToolsPanel(tk.Frame):
    def __init__(self,master=None):
      tk.Frame.__init__(self,master)
      self.open_close_btn_text = tk.StringVar()
      self.open_close_btn_text.set("Abrir FON Tools")
      self.open_close_btn = tk.Button(self,textvariable=self.open_close_btn_text,command=self.toggle_window)
      self.open_close_btn.pack()
      self.app_opened = False

    def toggle_window(self):
      self.app_opened = not self.app_opened
      if self.app_opened:
        self.new_window()
        self.open_close_btn_text.set("Cerrar FON Tools")
      else:
        self.del_window()
        self.open_close_btn_text.set("Abrir FON Tools")
      
    def new_window(self,event=None):
        self.app_window = FonToolsGUI(self)
        self.app_window.pack()

    def del_window(self,event=None):
        self.app_window.destroy()
        
if __name__=="__main__":
  app = FonToolsGUI()
  app.mainloop()