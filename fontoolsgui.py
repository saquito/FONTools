
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
      pageRisks = ttk.Frame(nb)
      pageUABombing = ttk.Frame(nb)
      nb.add(pageConfiguration, text='Configuration')
      nb.add(pageOverview, text='Overview')
      nb.add(pageExpansions, text='Expansions')
      nb.add(pageRisks, text='Risks')
      nb.add(pageUABombing, text='UA-Bombing')
      nb.pack(expand=1, fill="both")
      
      self.configuration_frame = ttk.PanedWindow(pageConfiguration)
      self.configuration_frame.updatedb_btn = ttk.Button(self.configuration_frame,text="Update Database",command=self.update_tick)
      self.configuration_frame.updatedb_btn.pack()
      self.configuration_frame.pack(expand=True, fill='both',side=LEFT)
      self.overview_frame = OverviewPanedWindow(pageOverview)

      self.conn = bgs.get_db_connection()
      
    def update_tick(self):
      update_tick()

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
        
class OverviewPanedWindow(tk.PanedWindow):
    def __init__(self,master=None):
        tk.PanedWindow.__init__(self,master)
        self.combo = ttk.Combobox(self)
        self.combo.pack(side=TOP)
        self.combo.bind("<<ComboboxSelected>>", self.overview_selection_changed)
        self.treeview = ttk.Treeview(self,columns=("Faction","Influence","State","Pending","Recovering","Player","Last Update"))
        self.treeview.heading("#0",text="#")
        self.treeview.column("#0",width=30,stretch=NO,anchor=CENTER)
        self.treeview.heading("Faction",text="Faction",anchor=CENTER)
        self.treeview.column("Faction",width=240,stretch=NO,anchor="w")
        self.treeview.heading("Influence",text="Influence",anchor=CENTER)
        self.treeview.column("Influence",width=50,stretch=NO,anchor=CENTER)
        self.treeview.heading("State",text="State",anchor=CENTER)
        self.treeview.column("State",width=150,stretch=NO,anchor=CENTER)
        self.treeview.heading("Pending",text="Pending",anchor=CENTER)
        self.treeview.column("Pending",width=240,stretch=NO,anchor=CENTER)
        self.treeview.heading("Recovering",text="Recovering",anchor=CENTER)
        self.treeview.column("Recovering",width=240,stretch=NO,anchor=CENTER)
        self.treeview.heading("Player",text="Player",anchor=CENTER)
        self.treeview.column("Player",width=140,stretch=NO,anchor=CENTER)
        self.treeview.heading("Last Update",text="Last Update",anchor=CENTER)
        self.treeview.column("Last Update",width=140,stretch=NO,anchor=CENTER)
        self.treeview.pack(expand=True, fill='both')
        self.treeview.bind('<<TreeviewSelect>>',self.selectItemCallback)
        self.pack(expand=True, fill='both',side=RIGHT)
        self.combo["values"] = ["Naunin", "HR 6177", "Ratemere", "Maopi", "Smethells 1"]
        self.conn = bgs.get_db_connection()
    
    def overview_selection_changed(self,event):
      system_name = self.combo.get()
      self.update_overview(system_name)
    
    def update_overview(self,system_name):
      self.treeview.delete(*self.treeview.get_children())
      i=0
      star_system = bgs.System(self.conn,system_name)
      if star_system:
        system_factions = star_system.get_current_factions(self.conn)
        for faction in system_factions:
          f = bgs.Faction(self.conn,faction)
          timestamp,influence = f.get_influence_in_system(self.conn, system_name)[0]
          active_state = f.get_states(self.conn,'activeState')[0][2]
          pending_states = ", ".join([state[2] for state in f.get_states(self.conn,'pendingState')])
          recovering_states = ", ".join([state[2] for state in f.get_states(self.conn,'recoveringState')])
          item = self.treeview.insert("", END, text=str(i), values=(f.name,influence*100.0,active_state,pending_states,recovering_states, "YES" if f.is_player else "NO",""))
          i=i+1
      
    def selectItemCallback(self,event):
      pass
      
def update_tick():
  bgs.update_tick()

def get_controlled_systems():
  return  ["Naunin", "HR 6177", "Ratemere", "Maopi", "Smethells 1"]
        
if __name__=="__main__":
  app = FonToolsGUI()
  app.mainloop()