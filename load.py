import sys
import Tkinter as tk
import myNotebook as nb
from config import config
import bgs
from fontoolsgui import FonToolsGUI

this = sys.modules[__name__]  # For holding module globals

def plugin_start(plugin_dir):
   """
   Load this plugin into EDMC
   """
   print "I am loaded! My plugin folder is {}".format(plugin_dir.encode("utf-8"))
   # later on your event functions can directly update this.status["text"]
   
   return "Test"

def plugin_stop():
    """
    EDMC is closing
    """
    print "Farewell cruel world!"

def plugin_prefs(parent, cmdr, is_beta):
   """
   Return a TK Frame for adding to the EDMC settings dialog.
   """
   this.mysetting = tk.IntVar(value=config.getint("MyPluginSetting"))  # Retrieve saved value from config
   frame = nb.Frame(parent)
   nb.Label(frame, text="Hello").grid()
   nb.Label(frame, text="Commander").grid()
   nb.Checkbutton(frame, text="My Setting", variable=this.mysetting).grid()

   return frame

def prefs_changed(cmdr, is_beta):
   """
   Save settings.
   """
   config.set('MyPluginSetting', this.mysetting.getint())  # Store new value in config
   
   this = sys.modules[__name__]  # For holding module globals

def plugin_app(parent):
   """
   Create a pair of TK widgets for the EDMC main window
   """
   #label = tk.Label(parent, text="Status:")
   #this.status = tk.Label(parent, anchor=tk.W, text="")
   this.app_frame = FonToolsGUI() #note that you don't have to explicitly specify a root
   this.app_frame.grid() #still have to grid the Frame to its master
   
   return (None,this.app_frame)
   