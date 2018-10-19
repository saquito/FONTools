
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
      self.expansions_frame = ExpansionsPanedWindow(pageExpansions)
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
        self.factions_tree = ttk.Treeview(self,columns=("Faction","Influence","State","Pending","Recovering","Player","Last Update"))
        self.factions_tree.heading("#0",text="#")
        self.factions_tree.column("#0",width=30,stretch=NO,anchor=CENTER)
        self.factions_tree.heading("Faction",text="Faction",anchor=CENTER)
        self.factions_tree.column("Faction",width=240,stretch=NO,anchor="w")
        self.factions_tree.heading("Influence",text="Influence",anchor=CENTER)
        self.factions_tree.column("Influence",width=50,stretch=NO,anchor=CENTER)
        self.factions_tree.heading("State",text="State",anchor=CENTER)
        self.factions_tree.column("State",width=150,stretch=NO,anchor=CENTER)
        self.factions_tree.heading("Pending",text="Pending",anchor=CENTER)
        self.factions_tree.column("Pending",width=240,stretch=NO,anchor=CENTER)
        self.factions_tree.heading("Recovering",text="Recovering",anchor=CENTER)
        self.factions_tree.column("Recovering",width=240,stretch=NO,anchor=CENTER)
        self.factions_tree.heading("Player",text="Player",anchor=CENTER)
        self.factions_tree.column("Player",width=140,stretch=NO,anchor=CENTER)
        self.factions_tree.heading("Last Update",text="Last Update",anchor=CENTER)
        self.factions_tree.column("Last Update",width=140,stretch=NO,anchor=CENTER)
        self.factions_tree.tag_configure("my_faction", background="#99FF99")
        self.factions_tree.pack(expand=True, fill='both')
        self.factions_tree.bind('<<TreeviewSelect>>',self.selectItemCallback)
        self.pack(expand=True, fill='both',side=RIGHT)
        self.combo["values"] = get_controlled_systems()
        if self.combo["values"]:
          self.combo.current(0)
          self.update_overview(self.combo.get())
        
    def get_controlled_systems(self):
      retun ["Naunin", "HR 6177", "Ratemere", "Maopi", "Smethells 1"]
      
    def overview_selection_changed(self,event):
      system_name = self.combo.get()
      self.update_overview(system_name)
    
    def update_overview(self,system_name):
      self.factions_tree.delete(*self.factions_tree.get_children())
      i=1
      star_system = bgs.System(system_name)
      if star_system:
        system_factions = star_system.get_current_factions()
        for faction in sorted(system_factions,key=lambda faction: bgs.Faction(faction).get_influence_in_system(system_name)[0][1],reverse=True):
          tags = []
          f = bgs.Faction(faction)
          timestamp,influence = f.get_influence_in_system(system_name)[0]
          active_state = f.get_states('activeState')[0][2]
          pending_states = ", ".join([state[2] for state in f.get_states('pendingState')])
          recovering_states = ", ".join([state[2] for state in f.get_states('recoveringState')])
          if faction == bgs.my_faction:
            tags.append("my_faction")
          item = self.factions_tree.insert("", END, text=str(i), values=(f.name, "{:.2%}".format(influence),0,active_state,pending_states,recovering_states, "YES" if f.is_player else "NO",""),tags=tags)
          i=i+1
      
    def selectItemCallback(self,event):
      pass
      
class ExpansionsPanedWindow(tk.PanedWindow):
    def __init__(self,master=None):
        tk.PanedWindow.__init__(self,master)
        
        self.home_system_label = ttk.Label(self,text="Home system")
        self.home_system_label.pack(side=LEFT)
        self.combo = ttk.Combobox(self)
        self.combo.pack(side=LEFT)
        self.faction_label = ttk.Label(self,text="Faction")
        self.faction_label.pack(side=BOTTOM)
        self.combo.bind("<<ComboboxSelected>>", self.overview_selection_changed)
        self.systems_tree = ttk.Treeview(self,columns=("System","Distance","Number of Factions","Has Player"))
        self.systems_tree.heading("#0",text="#")
        self.systems_tree.column("#0",width=30,stretch=NO,anchor=CENTER)
        self.systems_tree.heading("System",text="System",anchor=CENTER)
        self.systems_tree.column("System",width=240,stretch=NO,anchor="w")
        self.systems_tree.heading("Distance",text="Distance",anchor=CENTER)
        self.systems_tree.column("Distance",width=50,stretch=NO,anchor=CENTER)
        self.systems_tree.heading("Number of Factions",text="Number of Factions",anchor=CENTER)
        self.systems_tree.column("Number of Factions",width=150,stretch=NO,anchor=CENTER)
        self.systems_tree.heading("Has Player",text="Has Player",anchor=CENTER)
        self.systems_tree.column("Has Player",width=140,stretch=NO,anchor=CENTER)
        self.systems_tree.tag_configure("has_player", background="khaki")
        self.systems_tree.tag_configure("full", foreground="gray")
        self.systems_tree.tag_configure("next_expansion", background="#99FF99")
        self.systems_tree.pack(expand=True, fill='both')
        self.systems_tree.bind('<<TreeviewSelect>>',self.selectItemCallback)
        self.pack(expand=True, fill='both',side=RIGHT)
        self.combo["values"] = get_controlled_systems()
        if self.combo["values"]:
          self.combo.current(0)
          self.update_home_expansions(self.combo.get(), bgs.my_faction)
        
    def get_controlled_systems(self):
      retun ["Naunin", "HR 6177", "Ratemere", "Maopi", "Smethells 1"]
      
    def overview_selection_changed(self,event):
      system_name = self.combo.get()
      self.update_home_expansions(system_name,"Fathers of Nontime")
    
    def update_home_expansions(self,home_system_name=None,controller_faction=None):
      self.systems_tree.delete(*self.systems_tree.get_children())
      i=1
      if home_system_name:
        next_expansion_found = False
        for expansion_system in self.get_near_systems(home_system_name, controller_faction):
          if not expansion_system['controlled']:
            system_tags = []
            if expansion_system['num_factions'] >= 7:
              system_tags.append("full")
            elif not next_expansion_found:
              next_expansion_found = True
              system_tags.append("next_expansion")
            elif expansion_system['has_player']:
              system_tags.append("has_player")
            item = self.systems_tree.insert("", END, text=str(i), tags=system_tags,values=(expansion_system['name'],
                                                                          expansion_system['distance'],
                                                                          expansion_system['num_factions'],
                                                                          "YES" if expansion_system['has_player'] else "NO"))#, "YES" if f.is_player else "NO",""))
            i+=1
          
    def get_near_systems(self,system_name,controller_faction=None, number_of_systems=20):
      result = []
      star_system = bgs.System(system_name)
      if star_system:
        near_systems = star_system.get_closest_systems(number_of_systems)
        for near_sys in near_systems:
          factions = [faction for faction in bgs.System(near_sys["system"]).get_factions() if bgs.Faction(faction).get_influence_in_system(near_sys["system"])[0][1]>0]
          num_factions = len(factions)
          has_player_faction = False
          controlled = False
          for faction in factions:
            faction_obj = bgs.Faction(faction)
            if faction_obj.name == controller_faction:
              controlled = True
            if faction_obj.is_player:
              has_player_faction = True
          result.append({"name":near_sys["system"],"distance":near_sys["distance"],"num_factions":num_factions,"controlled":controlled,"has_player":has_player_faction})
      if result:
        result = sorted(result,key=lambda x: float(x["distance"]))
      return result
      
    def selectItemCallback(self,event):
      pass
      
def update_tick():
  bgs.update_tick()

def get_controlled_systems():
  return  ["Naunin", "HR 6177", "Ratemere", "Maopi", "Smethells 1"]
        
if __name__=="__main__":
  app = FonToolsGUI()
  app.mainloop()