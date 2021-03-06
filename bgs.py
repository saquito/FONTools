import requests
import json
import sqlite3
import os.path
import time
import datetime
import sys
import shutil
from collections import defaultdict
import itertools
from math import sqrt
from pprint import pprint
import configparser

this = sys.modules[__name__]
path = os.path.dirname(this.__file__)

config = {}

IS_FLASK_ENVIRONMENT = False

try:
  from . import db
  IS_FLASK_ENVIRONMENT = True
except:
  pass

config = configparser.ConfigParser(interpolation=None)
config.read("bgs.ini")




def get_config(option):
  return config["CONFIGURATION"][option]

CREATE_DATABASE_SQL = os.sep.join((path,"bgs-data.sqlite3.sql"))
DATABASE = os.sep.join((path,"bgs-data.sqlite3"))

FACTION_CONTROLLED = get_config("FACTION_CONTROLLED")
LOCAL_JSON_PATH = get_config("LOCAL_JSON_PATH")


EXPANSION_RADIUS = float(get_config("EXPANSION_RADIUS"))
EXPANSION_THRESHOLD = float(get_config("EXPANSION_THRESHOLD"))
EXPANSION_FACTION_THRESHOLD = int(get_config("EXPANSION_FACTION_THRESHOLD"))
EXPANSION_FACTION_MAX = int(get_config("EXPANSION_FACTION_MAX")) 
RETREAT_THRESHOLD = float(get_config("RETREAT_THRESHOLD"))
WAR_THRESHOLD = float(get_config("WAR_THRESHOLD"))
TICK_TIME = get_config("TICK_TIME")
TIME_FORMAT = get_config("TIME_FORMAT")
DATE_FORMAT = get_config("DATE_FORMAT")
DEBUG_LEVEL = int(get_config("DEBUG_LEVEL"))
BUBBLE_SYSTEMS = map(lambda x: x.strip(),get_config("BUBBLE_SYSTEMS").split(","))

print ("=========",DATABASE,"========")

this.conn = None

def distance(p0,p1):
  x0,y0,z0 = p0
  x1,y1,z1 = p1
  return abs(sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2 + (z1 - z0) ** 2))

def debug(message,level = 0):
  if level <= DEBUG_LEVEL:
    print(message)

def clean_local_json_path():
  if os.path.exists(LOCAL_JSON_PATH):
    shutil.rmtree(LOCAL_JSON_PATH)
    

def get_local_json_path(filename):
  if not os.path.exists(LOCAL_JSON_PATH):
    os.mkdir(LOCAL_JSON_PATH)
  return "/".join((LOCAL_JSON_PATH,filename))

def get_json_data(filename,request, request_data, local = False):
  data = None
  json_file_path = get_local_json_path(filename)
  if local and os.path.isfile(json_file_path):
      json_file = open(json_file_path,"r")
      data = json.load(json_file)
  else:
    r = requests.post(request, request_data)
    data = json.loads(r.text)
    if r.text == "[]":
      print(r.headers)
      exit(-1)
    json_file = open(json_file_path,"w")
    json_file.write(json.dumps(data))
    json_file.close()
  return data

def get_db_connection(database=DATABASE):
  if not this.conn:
    this.conn = sqlite3.connect(database)
  return this.conn

def get_db_cursor(database=DATABASE):
  conn = get_db_connection(database)
  return conn.cursor()

def create_database(database=DATABASE):
  sql = open(CREATE_DATABASE_SQL,'r').read()
  c = get_db_cursor(database)
  for statement in sql.split(";"):
    print(statement)
    c.execute(statement)
  
def fetch_system(systemName):
  c = get_db_cursor()
  c.execute("SELECT * FROM Systems WHERE system_name=:name",{'name':systemName})
  data = c.fetchone()
  return data

def fetch_faction(factionName):
  c = get_db_cursor()
  c.execute("SELECT * FROM Factions WHERE faction_name=:name",{'name':factionName})
  data = c.fetchone()
  return data

def fill_factions_from_system(systemName, local = False):
  conn = get_db_connection()
  c = conn.cursor()
  data_factions = get_json_data("factions_{0}.json".format(systemName),
                       "https://www.edsm.net/api-system-v1/factions",
                       {'systemName': systemName, 'showHistory':1}, 
                       local)
  if not data_factions['factions']:
    return None
  for faction in data_factions['factions']:
    if not fetch_faction(faction['name']):
      values = [faction['name'],faction['allegiance'],faction['government'],faction['isPlayer'], None]
      c.execute("INSERT INTO Factions VALUES (?,?,?,?,?)",values)
  conn.commit()

def fill_systems_in_bubble(systemName, radius = EXPANSION_RADIUS, local = False): 
  conn = get_db_connection()
  c = conn.cursor()
  debug("RADIUS:",radius)
  data_bubble = get_json_data("sphere_{0}.json".format(systemName),
                       "https://www.edsm.net/api-v1/sphere-systems",
                       {'systemName': systemName,'radius':radius}, 
                       local)
  for system in data_bubble:
    distance = system['distance']
    data_system = get_json_data("system_{0}.json".format(system['name']),
                   "https://www.edsm.net/api-v1/system",
                   {'systemName': system['name'],'showPrimaryStar':1,'showInformation':1,"showCoordinates":1}, 
                   local)
    population = 0
    economy = 'None'
    
    if data_system['information']:
      x,y,z = (0,0,0)
      if data_system['coords']:
        x,y,z = data_system['coords']['x'],data_system['coords']['y'],data_system['coords']['z']
      population = data_system['information']['population']
      economy = data_system['information']['economy']
      allegiance = data_system['information']['allegiance']
      faction = data_system['information']['faction']
      factionState = data_system['information']['factionState']
      values = [data_system['name'],
                population,
                economy,distance,allegiance,faction,factionState,x,y,z] 
      try:
        c.execute("INSERT INTO Systems VALUES (?,?,?,?,?,?,?,?,?,?)",values)
      except sqlite3.IntegrityError:
        pass
    data_stations = get_json_data("stations_{0}.json".format(system['name']),
                     "https://www.edsm.net/api-system-v1/stations",
                     {'systemName': system['name']}, 
                     local)
    for station in data_stations['stations']:
      controlling_faction = None
      if 'controllingFaction' in station:
        controlling_faction = station['controllingFaction']['name']
      values = [systemName,station['name'],station['type'],station['distanceToArrival'],station['economy'],controlling_faction]
      try:
        c.execute("INSERT INTO Stations VALUES (?,?,?,?,?,?)",values)
      except sqlite3.IntegrityError:
        pass
    debug("Updating system: {0}".format(system['name']))
    fill_factions_from_system(data_system['name'], local)
  conn.commit()

def get_systems(criteria = None):
    c = get_db_cursor()
    if criteria:
      c.execute("SELECT * FROM Systems WHERE {0}".format(criteria))
    else:
      c.execute("SELECT * FROM Systems")  
    return c.fetchall()

def clean_updates():
  conn = get_db_connection()
  c = conn.cursor()
  c.execute("DELETE FROM ticks")
  c.execute("DELETE FROM faction_system")
  c.execute("DELETE FROM system_status")
  c.execute("DELETE FROM faction_state")
  conn.commit()

def clean_fixed_tables():
  conn = get_db_connection()
  c = conn.cursor()
  c.execute("DELETE FROM Factions")
  c.execute("DELETE FROM Systems")
  c.execute("DELETE FROM Stations")
  conn.commit()

def get_days(timestamp1,timestamp2):
  params1 = [int(num) for num in get_date_from_epoch(timestamp1).split("-")]
  params2 = [int(num) for num in get_date_from_epoch(timestamp2).split("-")]
  d1 = datetime.date(*params1)
  d2 = datetime.date(*params2)
  delta = d2 - d1
  return abs(delta.days)

def get_time(cur_time = None):
  current_time = time.time()
  if cur_time != None:
    if isinstance(cur_time,str):
      current_time = get_epoch_from_utc_time(cur_time)
    elif isinstance(cur_time,float) or isinstance(cur_time,int):
      current_time = cur_time
    else:
      print("DATE FORMAT ERROR")
      exit(-1)
  return current_time

def get_last_tick_time(cur_time = None):
  current_time = get_time(cur_time)
  
  todays_tick_time = get_todays_tick_time(current_time)
  if current_time >= todays_tick_time:
    return todays_tick_time
  else:
    todays_tick_datetime = datetime.datetime.fromtimestamp(todays_tick_time)
    tomorrows_tick_datetime = todays_tick_datetime - datetime.timedelta(days=1)
    return tomorrows_tick_datetime.timestamp()
    
def get_next_tick_time(cur_time = None):
  current_time = get_time(cur_time)
  
  todays_tick_time = get_todays_tick_time(current_time)
  if current_time < todays_tick_time:
    return todays_tick_time
  else:
    todays_tick_datetime = datetime.datetime.fromtimestamp(todays_tick_time)
    tomorrows_tick_datetime = todays_tick_datetime + datetime.timedelta(days=1)
    return tomorrows_tick_datetime.timestamp()

def get_current_tick_time(cur_time = None):
  current_time = get_time(cur_time)
  
  todays_tick_time = get_todays_tick_time(current_time)
  last_tick_time = get_last_tick_time(current_time)
  if current_time <= todays_tick_time:
    return last_tick_time
  else:
    return todays_tick_time    
  
def get_todays_tick_time(cur_time = None):
  current_time = get_time(cur_time)
  
  day_time = time.strftime("%d-%m-%Y",time.gmtime(current_time))
  if cur_time:
    day_time = time.strftime("%d-%m-%Y",time.gmtime(cur_time))
  todays_tick_time = " ".join((day_time,TICK_TIME))
  return get_epoch_from_utc_time(todays_tick_time)

def is_update_needed(cur_time = None):
  current_time = time.time()
  if cur_time:
    if isinstance(cur_time,str):
      current_time = get_epoch_from_utc_time(cur_time)
    elif isinstance(cur_time,float) or isinstance(cur_time,int):
      current_time = cur_time
    else:
      print("DATE FORMAT ERROR")
      return False
  last_update_time = get_last_update()
  todays_tick_time = get_todays_tick_time(current_time)
  current_tick_time = get_current_tick_time(current_time)
  next_tick_time = get_next_tick_time(current_time)
  last_tick_time = get_last_tick_time(cur_time)
  debug("CURRENT_TIME:\t\t{0} [{1}]".format(int(current_time),get_utc_time_from_epoch(current_time)))
  debug("LAST_UPDATE_TIME:\t{0} [{1}]".format(int(last_update_time),get_utc_time_from_epoch(last_update_time)))
  debug("TODAYS_TICK_TIME:\t{0} [{1}]".format(int(todays_tick_time),get_utc_time_from_epoch(todays_tick_time)))
  debug("LAST_TICK_TIME:\t\t{0} [{1}]".format(int(next_tick_time),get_utc_time_from_epoch(last_tick_time)))
  debug("CURRENT_TICK_TIME:\t{0} [{1}]".format(int(current_tick_time),get_utc_time_from_epoch(current_tick_time)))
  debug("NEXT_TICK_TIME:\t\t{0} [{1}]".format(int(next_tick_time),get_utc_time_from_epoch(next_tick_time)))
  

  if last_update_time == 0:
    return True
  if last_update_time < last_tick_time:
    return True
  if current_time > last_update_time and last_update_time < todays_tick_time:
    if current_time < todays_tick_time:
      return False
    else:
      return True
  else:
    return False

def get_utc_time_from_epoch(epoch):
  if isinstance(epoch,str):
    epoch = int(epoch)
  return time.strftime(TIME_FORMAT,time.gmtime(epoch))

def get_date_from_epoch(epoch):
  if isinstance(epoch,str):
    epoch = int(epoch)
  return time.strftime(DATE_FORMAT,time.gmtime(epoch))

def get_epoch_from_utc_time(utc_time):
  return time.mktime(time.strptime(utc_time, TIME_FORMAT))

def get_timestamp(cur_time = None):
  current_time = time.time()
  if cur_time:
    if isinstance(cur_time,str):
      current_time = get_epoch_from_utc_time(cur_time)
    elif isinstance(cur_time,float) or isinstance(cur_time,int):
      current_time = cur_time
    else:
      print("DATE FORMAT ERROR")
      exit(-1)
  return int(current_time)

def time_functions_test():
  for test_check_time in ["10-02-2018 13:29:00",
                  "10-02-2018 13:30:00",
                  "10-02-2018 13:35:00",
                  "11-02-2018 13:29:00",
                  "11-02-2018 13:30:00",
                  "11-02-2018 13:38:00",
                  "9-02-2018 13:30:00"]:
    debug("UPDATE NEEDED: {0}".format(is_update_needed(get_timestamp(test_check_time))))
    debug('*'*80)

def get_last_update():
  c = get_db_cursor()
  last_update = c.execute("SELECT MAX(timestamp) FROM ticks").fetchone()[0]
  if not last_update:
    last_update = 0

  return last_update

def update_system(systemName, local = False):
  data_system = get_json_data("system_{0}.json".format(systemName),
                   "https://www.edsm.net/api-v1/system",
                   {'systemName': systemName,'showPrimaryStar':1,'showInformation':1}, 
                   local)
  return data_system

def update_state_entry(timestamp,state_name,state_type,faction_name, trend):
  conn = get_db_connection()
  c = conn.cursor()
  values = [timestamp,state_name,state_type,faction_name, trend]
  c.execute("INSERT INTO faction_system_state VALUES",values)
  c.commit()

def update_tick(cur_time = None, local = False, history = False,forced=False):
  conn = get_db_connection()
  current_time = get_timestamp(cur_time)
  c = conn.cursor()
  if not forced:
    if not is_update_needed(current_time) and not history:
      debug("UPDATE NOT NEEDED")
      return False
    else:
      debug("UPDATE NEEDED")
  else:
    debug("UPDATE FORCED")
  if not history:
    print("update TICK")
    c.execute("INSERT INTO ticks VALUES (?)",[current_time])
  star_systems = get_systems("population > 0 ORDER BY population")
  total_systems = len(star_systems)
  current_start_system = 1
  for star_system in star_systems:
    systemName = star_system[0]
    system_info = update_system(systemName)
    sys.stdout.write("Updating System {0} [{1}/{2}]           \r".format(systemName,current_start_system,total_systems))
    current_start_system += 1
    sys.stdout.flush()
    values = [current_time,systemName,system_info['information']['faction'],system_info['information']['security']]
    if not history:
      c.execute("INSERT INTO system_status VALUES (?,?,?,?)",values)
    
    data_factions = get_json_data("factions_{0}.json".format(systemName),
                         "https://www.edsm.net/api-system-v1/factions",
                         {'systemName': systemName,'showHistory':1}, 
                         local)
    if not data_factions['factions']:
      return False
    
    for faction in data_factions['factions']:
      system_faction_entries = []
      active_state_entries = []
      pending_state_entries = []
      recovering_state_entries = []  
      if history:
        for timestamp in faction['stateHistory']:
          state = faction['stateHistory'][timestamp]
          active_state_entries.append([int(timestamp),state,'activeState',faction['name'],0])
        for timestamp in faction['influenceHistory']:
          system_faction_entries.append([int(timestamp),
            faction['name'],
            systemName,
            faction['influenceHistory'][timestamp]])
        if faction['recoveringStatesHistory']:
          for timestamp,state in faction['recoveringStatesHistory'].items():
            if not state:
              continue
            state = state[0]
            recovering_state_entries.append([int(timestamp),
                                  state['state'],
                                  "recoveringState",
                                  faction['name'],
                                  state['trend']])
        if faction['pendingStatesHistory']:
          for timestamp,state in faction['pendingStatesHistory'].items():
            if not state:
              continue
            state = state[0]
            pending_state_entries.append([int(timestamp),
                                  state['state'],
                                  "pendingState",
                                  faction['name'],
                                  state['trend']])
      else: 
        system_faction_entries.append([current_time,
                                        faction['name'],
                                        systemName,
                                        faction['influence']])
        active_state_entries.append([current_time,faction['state'],'activeState',faction['name'],0])
        for state in faction['pendingStates']:
          pending_state_entries.append([current_time,
                                state['state'],
                                "pendingState",
                                faction['name'],
                                state['trend']])
        for state in faction['recoveringStates']:
          recovering_state_entries.append([current_time,
                                state['state'],
                                "recoveringState",
                                faction['name'],
                                state['trend']])
      for values in system_faction_entries:
        if history:
          check_query = """
          SELECT * FROM faction_system WHERE
          date={0} AND
          name="{1}" AND
          system="{2}" AND
          influence={3}""".format(*values)
          c.execute(check_query)
          if c.fetchone():
            #debug("ENTRY_ALREADY_EXISTS")
            continue
        c.execute("INSERT INTO faction_system VALUES (?,?,?,?)",values)

      for values in active_state_entries:
        entry_timestamp,entry_state,entry_state_type,entry_faction, entry_trend = values
        if not c.execute("SELECT date,faction_name,state_type=':state_type' from faction_state WHERE date=:date AND faction_name=':faction' AND state_type=':state_type'",{'date':entry_timestamp,'faction':entry_faction,'state_type':entry_state_type}).fetchall():
          try:
            c.execute("INSERT INTO faction_state VALUES (?,?,?,?,?)",values)
          except:
            pass
            #print("State for {0} already updated".format(entry_faction))
      for values in pending_state_entries:
        entry_timestamp,entry_state,entry_state_type,entry_faction, entry_trend = values
        if not c.execute("SELECT date,faction_name,state_type=':state_type' from faction_state WHERE date=:date AND faction_name=':faction' AND state_type=':state_type'",{'date':entry_timestamp,'faction':entry_faction,'state_type':entry_state_type}).fetchall():
          try:
            c.execute("INSERT INTO faction_state VALUES (?,?,?,?,?)",values)
          except:
            pass
            #print("State for {0} already updated".format(entry_faction))
      for values in recovering_state_entries:
        entry_timestamp,entry_state,entry_state_type,entry_faction, entry_trend = values
        if not c.execute("SELECT date,faction_name,state_type=':state_type' from faction_state WHERE date=:date AND faction_name=':faction' AND state_type=':state_type'",{'date':entry_timestamp,'faction':entry_faction,'state_type':entry_state_type}).fetchall():
          try:
            c.execute("INSERT INTO faction_state VALUES (?,?,?,?,?)",values)
          except:
            pass
            #print("State for {0} already updated".format(entry_faction))
        
        if history:  
          conn.commit()
  conn.commit()
  return True

def get_system_status(systemName,timestamp  = None):
  if not timestamp:
    timestamp = get_last_update()
  else:
    timestamp = get_timestamp(timestamp)
    c = get_db_cursor()
  c.execute("""SELECT DISTINCT faction_system.date,
                        faction_system.system,
                        faction_system.name,
                        faction_system.influence,
                        faction_system.state,
                        faction_system_state.state_name,
                        faction_system_state.state_type
                  FROM faction_system, faction_system_state
                  WHERE faction_system.system = '{0}'
                  AND faction_system_state.system_name = '{0}'
                  AND faction_system.date = {1}
                  AND faction_system_state.date = {1}""".format(systemName,timestamp))
  return [systemName,c.fetchall()]

def get_system_status_timespan(systemName, initialTimestamp,endTimestamp = None):
  if not endTimestamp:
    endTimestamp = get_time()
  c = get_db_cursor()
  query = '''SELECT DISTINCT faction_system.date,
                        faction_system.system,
                        faction_system.name,
                        faction_system.influence,
                        faction_system.state,
                        faction_system.controller,
                        faction_system_state.state_name,
                        faction_system_state.state_type,
                        faction_system_state.trend
                  FROM faction_system, faction_system_state
                  WHERE faction_system.system = "{0}"
                  AND faction_system_state.system_name = "{0}"'''.format(systemName)
  c.execute(query)  
  all_entries = c.fetchall()
  return [systemName,[ entry for entry in all_entries if entry[0] >= initialTimestamp and entry[0] < endTimestamp]]

def get_all_entries():
  c = get_db_cursor()
  c.execute("SELECT * FROM faction_system")  
  return c.fetchall()


class Faction:
  def __init__(self,faction_name):
    c = get_db_cursor()
    self.name = faction_name
    self.ok = False
    self.json = ""
    c.execute('SELECT allegiance,government,is_player,native_system FROM Factions WHERE faction_name = "{0}"'.format(faction_name))
    try:
      self.allegiance, self.government, self.is_player, self.native_system = c.fetchone()
      self.ok = True
    except:
      self.ok = False
    if self.ok:
      self.json = {"name":self.name,"allegiance":self.allegiance,"government":self.government,"isPlayer":self.is_player,"native_system":self.native_system}
  def __repr__(self):
    return str(self.json)

  @classmethod
  def get_all_factions(cls,criteria=None):
    criteria_sql = ""
    if criteria:
      if isinstance(criteria, (list,tuple)):
        criteria_sql = " WHERE " + " AND ".join(criteria)
      elif isinstance(criteria,str):
        criteria_sql = " WHERE " + criteria
      else:
        return None
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT faction_name FROM Factions{0}'.format(criteria_sql))
    factions = c.fetchall()
    factions = [Faction(faction[0]) for faction in factions]
    return factions
  
  def get_retreat_risk(self,threshold = RETREAT_THRESHOLD):
    systems = self.get_systems()
    risked = []
    if systems:
      for system_name in systems:
        influence = self.get_status_in_system(system_name).popitem()[1]['status']['influence']
        if influence > 0.0 and influence < threshold:
          risked.append([system_name,influence])
    return(risked)
  
  def get_expansion_risk(self,threshold = EXPANSION_THRESHOLD):
    systems = self.get_systems()
    risked = []
    if systems:
      for system_name in systems:     
        influence = self.get_status_in_system(system_name).popitem()[1]['status']['influence']
        if influence > threshold:
          risked.append([system_name,influence])
      return(risked)
  
  def get_expansion_risk_system(self,system,threshold = EXPANSION_THRESHOLD):
    systems = self.get_systems()
    risked = []
    if systems:
      for system_name in systems:     
        influence = self.get_status_in_system(system_name).popitem()[1]['status']['influence']
        if influence > threshold:
          risked.append([system_name,influence])
      return(risked)
  
  def get_systems(self, start_timestamp = None, end_timestamp = None):
    if not self.ok:
        return None  
    c = get_db_cursor()
    if start_timestamp == None:
      start_timestamp = get_last_update()
    else:
      start_timestamp = get_time(start_timestamp)
    if end_timestamp == None:
      end_timestamp = get_last_update()
      
    else:
      end_timestamp = get_time(end_timestamp)
    c.execute('SELECT DISTINCT system FROM faction_system WHERE name = "{0}" AND date >= {1} AND date <= {2}'.format(self.name,start_timestamp,end_timestamp))
    systems = [system[0] for system in c.fetchall() ]
    return(systems)
  
  def get_current_influence_in_system(self, system_requested):
    if not self.ok:
      return None
    if isinstance(system_requested,System):
      system_requested = system_requested.name
    c = get_db_cursor()
    c.execute('SELECT influence FROM faction_system WHERE system = "{0}" AND name = "{1}" ORDER BY date'.format(system_requested,self.name,get_last_update()))  
    influence_data = c.fetchone()
    if influence_data and len(influence_data) > 0: 
      return influence_data[0]
    return None
  
  def get_influence_in_system(self,system_requested, start_timestamp = None, end_timestamp = None):
    if not self.ok:
      return None
    c = get_db_cursor()
    if start_timestamp == None:
      start_timestamp = get_last_update()
    else:
      start_timestamp = get_time(start_timestamp)
    if end_timestamp == None:
      end_timestamp = get_last_update()
      
    else:
      end_timestamp = get_time(end_timestamp)
    if isinstance(system_requested,System):
      system_requested = system_requested.name
    
    c.execute('SELECT date,influence FROM faction_system WHERE system = "{0}" AND name = "{1}" AND date >= {2} AND date <= {3}'.format(system_requested,self.name,start_timestamp,end_timestamp))  
    influence_data = c.fetchall()
    if influence_data and len(influence_data) > 0: 
      return influence_data
    return None
  
  def get_current_pending_states(self):
    if not self.ok:
        return None
    c = get_db_cursor()
    c.execute('SELECT DISTINCT state_name, trend FROM faction_state WHERE faction_name = "{0}" AND date ={1} AND state_type="pendingState"'.format(self.name,get_last_update()))
    return c.fetchall()
  
  def get_current_recovering_states(self):
    if not self.ok:
        return None
    c = get_db_cursor()
    c.execute('SELECT DISTINCT state_name, trend FROM faction_state WHERE faction_name = "{0}" AND date ={1} AND state_type="recoveringState"'.format(self.name,get_last_update()))
    return c.fetchall()
  
  def get_states(self, state_type=None, start_timestamp = None, end_timestamp = None):
    c= conn.cursor()
    if start_timestamp == None:
      start_timestamp = get_last_update()
    else:
      start_timestamp = get_time(start_timestamp)
    if end_timestamp == None:
      end_timestamp = 0xFFFFFFFF
    if not state_type or state_type not in ["pendingState","recoveringState","activeState"]:
      states  = c.execute('SELECT date, state_type, state_name FROM faction_state WHERE faction_name ="{0}"  AND date >= {1} AND date <= {2} ORDER BY date DESC'.format(self.name,start_timestamp,end_timestamp)).fetchall()
    else:
      states  = c.execute('SELECT date, state_type, state_name FROM faction_state WHERE state_type = "{3}" AND faction_name ="{0}"  AND date >= {1} AND date <= {2} ORDER BY date DESC'.format(self.name,start_timestamp,end_timestamp,state_type)).fetchall()
         
    return states
  
  def get_state_history(self,start_timestamp = None, end_timestamp = None):
    result = self.get_states()
    return result
  
  def get_state(self):
    result = self.get_states()
    if isinstance(result[0],sqlite3.Row):
      result = tuple(result[0])
    return result
  
  def get_status_in_system(self,system_name, start_timestamp = None, end_timestamp = None):
    if not self.ok:
        return None
    c = get_db_cursor()
    if start_timestamp == None:
      start_timestamp = get_last_update()
    else:
      start_timestamp = get_time(start_timestamp)
    if end_timestamp == None:
      end_timestamp = get_last_update()
    else:
      end_timestamp = get_time(end_timestamp)

    timestamps = defaultdict(dict)
    c.execute('SELECT date,influence FROM faction_system WHERE name = "{0}" AND system = "{1}" AND date >= {2} AND date <= {3}'.format(self.name,system_name,start_timestamp,end_timestamp))
    status_entries =  list(c.fetchall())
    c.execute('SELECT date,state_name,state_type,trend FROM faction_state WHERE faction_name = "{0}" AND date >= {1} AND date <= {2}'.format(self.name,start_timestamp,end_timestamp))
    state_entries = list(c.fetchall())
    for entry in state_entries:
      timestamp,state_name,state_type,trend = entry
      timestamp = str(int(float(timestamp)))
      timestamps[timestamp][state_type + 's'] = {'state':state_name, 'trend':trend}
    for entry in status_entries:
      timestamp,influence = entry
      timestamp = str(int(float(timestamp)))
      timestamps[timestamp]['status'] = {'influence':influence,'state':state_name}
    return timestamps

class System:
  def __init__(self,system_name):
    self.name = system_name
    self.ok = False
    self.json = ""
    c = get_db_cursor()
#    try:
    result = c.execute('SELECT population,economy,distance,x,y,z FROM Systems WHERE name = "{0}"'.format(system_name)).fetchone()
    self.population, self.economy, self.distance, self.x, self.y, self.z = result
    self.ok = True
#    except:
#      print("ERROR getting data!!!")
    if self.ok:
      self.json =  {"name":self.name,"population":self.population,"economy":self.economy,"distance":self.distance}
  
  @classmethod
  def get_all_systems(cls):
    c = get_db_cursor()
    c.execute('SELECT name FROM Systems')
    factions = [System(faction[0]) for faction in c.fetchall()]
    return factions 
  
  def get_closest_systems(self,limit = None):
    if not self.ok:
      return None
    all_systems = System.get_all_systems()
    system_list = []
    for near_system in all_systems:
      system_list.append({"system":near_system.name,"distance":distance([near_system.x,near_system.y,near_system.z],[self.x,self.y,self.z])})
    return sorted(system_list,key=lambda x:[x["distance"]])[1:limit]
  
  def get_next_expansion_system(self):
    for candidate in self.get_closest_systems():
      candidate_system = System(candidate["system"])
      if len(candidate_system.get_factions()) <= EXPANSION_FACTION_THRESHOLD:
        return({"system":candidate["system"],"distance":candidate["distance"]})
      else:
        print(candidate,"- NO:",len(candidate_system.get_factions()),"factions")
  
  def get_controller_and_state(self,timestamp = None):
    c = get_db_cursor()
    if not self.ok:
      return None
    if not timestamp:
      timestamp = get_last_update()
    faction_name = c.execute('SELECT controller_faction FROM system_status WHERE system = "{0}" AND date = "{1}"'.format(self.name,timestamp)).fetchone()[0]
    state = c.execute('SELECT state_name FROM faction_state WHERE faction_name ="{0}" AND date = "{1}"'.format(faction_name,timestamp)).fetchone()[0]
    return {"name":faction_name,"state":state}
    
  def get_war_risk(self,threshold = WAR_THRESHOLD):
    factions = self.get_factions()
    factions_in_risk = []
    if factions:
      for faction1,faction2 in itertools.combinations(factions,2):
        influence1 = Faction(faction1).get_current_influence_in_system(self.name)
        influence2 = Faction(faction2).get_current_influence_in_system(self.name)
        if influence1 and influence2:
          if (faction1 == self.get_controller_and_state()['name'] and influence2 > influence1) or (faction2 == self.get_controller_and_state()['name'] and influence1 > influence2):
            factions_in_risk.append([faction1,faction2,"Overrule"])
          elif abs(influence1 - influence2) < threshold:
            factions_in_risk.append([faction1,faction2,"Close"])
        
    return factions_in_risk
      
  def get_factions(self, start_timestamp = None, end_timestamp = None):
    if not self.ok:
      return None
    c = get_db_cursor()
    if start_timestamp == None:
      start_timestamp = get_last_update()
    else:
      start_timestamp = get_time(start_timestamp)
    if end_timestamp == None:
      end_timestamp =0xFFFFFFFF
    else:
      end_timestamp = get_time(end_timestamp)
    c.execute('SELECT name FROM faction_system WHERE system = "{0}" AND date >= {1} AND date <= {2} AND influence > 0.0'.format(self.name,start_timestamp,end_timestamp))
    factions = [tuple(faction)[0] for faction in c.fetchall()]
    return factions
  
  def get_current_factions(self, start_timestamp = None, end_timestamp = None):
    return self.get_factions(start_timestamp,end_timestamp)
    
  def __repr__(self):
    return str(self.json)

def get_factions_with_retreat_risk(threshold = RETREAT_THRESHOLD):
  ret_risked = []
  for faction in Faction.get_all_factions():
    risked = faction.get_retreat_risk(threshold)
    if risked:
      for system in risked:
        system_name, influence = system
        if not faction.name.startswith(system_name):
          ret_risked.append({"faction":faction.name,"system":system_name,"influence":influence, "state":faction.get_state()})
  return ret_risked

def get_factions_with_expansion_risk(threshold=EXPANSION_THRESHOLD):

  ret_risked = []
  for faction in Faction.get_all_factions():
    risked = faction.get_expansion_risk(threshold)
    if risked:
      for system in risked:
        system_name, influence = system
        ret_risked.append({"faction":faction.name,"system":system_name,"influence":influence, "state":faction.get_state()})
  return ret_risked

def get_trend_text(trend):
  if trend == 0:
    return "="
  elif trend > 0:
    return "+"
  else:
    return "-"

def get_retreat_risk_report(threshold = None):
  if not threshold:
    threshold = RETREAT_THRESHOLD
  data = []
  report = "\n" + "*"*10 + "RETREAT RISK REPORT" + "*"*10 + "\n\n"
  report += "The following factions are in risk of enter in state of Retreat:\n"
  for risk in get_factions_with_retreat_risk(threshold):
    pending_states = ", ".join(["{0} ({1})".format(pending_state, get_trend_text(trend)) for pending_state, trend in Faction(risk['faction']).get_current_pending_states()])
    if not pending_states:
      pending_states = "None"
    recovering_states = ", ".join(["{0} ({1})".format(recovering_state,get_trend_text(trend)) for recovering_state, trend in Faction(risk['faction']).get_current_recovering_states()])
    if not recovering_states:
      recovering_states = "None"
    data.append([risk['faction'],risk['system'],risk['influence'],risk['state'][0][2], pending_states, recovering_states,System(risk['system']).distance])
    report += "'{0}' in system '{1}' (Influence: {2:.3g} %, State: {3}, Pending: {4}, Recovering: {5}, Distance: {6} lys)\n".format(risk['faction'],risk['system'],risk['influence']*100.0,risk['state'], pending_states, recovering_states,System(risk['system']).distance)
  return data

def get_war_risk_report(threshold = None):
  if not threshold:
    threshold = WAR_THRESHOLD
  data = []
  conn = get_db_connection()
  report = "\n" + "*"*10 + "WAR RISK REPORT" + "*"*10 + "\n"
  report += "The following factions are in risk of enter in state of War:\n"
  for system in System.get_all_systems():
    for faction1_name, faction2_name, reason in system.get_war_risk(threshold):
      faction1,faction2 = Faction(faction1_name), Faction(faction2_name)
      data.append([reason,faction1.name, faction1.get_current_influence_in_system(system.name),
                                                                  faction2.name,faction2.get_current_influence_in_system(system.name),system.name])
      report += "'{0}' ({1:.2f}%) versus '{2}' ({3:.2f}%) in '{4}'\n".format(faction1.name, faction1.get_current_influence_in_system(system.name),
                                                                  faction2.name,faction2.get_current_influence_in_system(system.name),system.name)
  return data

def get_expansion_risk_report(threshold = None):
  if not threshold:
    threshold = EXPANSION_THRESHOLD
  data = []
  conn = get_db_connection()
  report = "\n" + "*"*10 + "EXPANSION RISK REPORT" + "*"*10 + "\n"
  for risk in get_factions_with_expansion_risk(threshold):
    data.append([risk['faction'],risk['system'],risk['influence'],risk['state'][0][2], System(risk['system']).distance])
  return data



def fresh_hard_update(local = False,history=False):
  conn = get_db_connection()
  clean_fixed_tables()
  clean_updates()
  for controlled_system in BUBBLE_SYSTEMS:
    fill_systems_in_bubble(controlled_system, EXPANSION_RADIUS, local)
  update_tick(history=history)
  
if 0:
  conn = sqlite3.connect(DATABASE)
  
  fresh_start = False
  
  systemName = "Naunin"
  if fresh_start:
    clean_fixed_tables()
    clean_updates()
  #clean_local_json_path()
    fill_systems_in_bubble(systemName,EXPANSION_RADIUS,local=True)
    update_tick(get_timestamp("23-02-2018 13:30:00"),local = True,history = True)
  update_tick()
  
  if 0:
    defence = Faction("Defence Party of Naunin")
    print(defence)  
    
    for faction in Faction.get_all_factions(('faction_name LIKE "%Naunin%"')):
      print(faction)
    
  
  
    print(System.get_all_systems())
    
    my_system = System("Maopi")
    f = Faction('Naunin Jet Netcoms Incorporated')
    
    kb = Faction("Kupol Bumba Alliance")
    print(kb)
    print(kb.get_current_influence_in_system("Naunin"))
    
   
  if 1:
    f = Faction('Movement for Ngalu Democrats')
    print("PENDING STATES:",f.get_current_pending_states())
    print("RECOVERING STATES:",f.get_current_recovering_states())
    current_system = System(systemName)
    factions = current_system.get_factions()

    print(get_retreat_risk_report(0.025))
    print(get_war_risk_report(0.01))
    print(get_expansion_risk_report(0.65))

  systemName = "Naunin"
  for faction in System(systemName).get_factions():
    print(faction.name)
    status_history = faction.get_status_in_system(systemName,start_timestamp=0)
    if status_history:
      for entry in sorted(status_history):
        print(get_utc_time_from_epoch(entry),status_history[entry])
 
 
def fetch_bubble(systemName, radius = EXPANSION_RADIUS, local = False): 
  conn = get_db_connection()
  c = conn.cursor()
  debug("RADIUS:",radius)
  data_bubble = get_json_data("sphere_{0}.json".format(systemName),
                       "https://www.edsm.net/api-v1/sphere-systems",
                       {'systemName': systemName,'radius':radius}, 
                       local)
  for system in data_bubble:
    distance = system['distance']
    data_system = get_json_data("system_{0}.json".format(system['name']),
                   "https://www.edsm.net/api-v1/system",
                   {'systemName': system['name'],'showPrimaryStar':1,'showInformation':1,"showCoordinates":1}, 
                   local)
    population = 0
    economy = 'None'
    
    if data_system['information']:
      x,y,z = (0,0,0)
      if data_system['coords']:
        x,y,z = data_system['coords']['x'],data_system['coords']['y'],data_system['coords']['z']
      population = data_system['information']['population']
      economy = data_system['information']['economy']
      allegiance = data_system['information']['allegiance']
      faction = data_system['information']['faction']
      factionState = data_system['information']['factionState']
      values = [data_system['name'],
                population,
                economy,distance,allegiance,faction,factionState,x,y,z] 
      try:
        c.execute("INSERT INTO Systems VALUES (?,?,?,?,?,?,?,?,?,?)",values)
      except sqlite3.IntegrityError:
        pass
      data_stations = get_json_data("stations_{0}.json".format(system['name']),
                       "https://www.edsm.net/api-system-v1/stations",
                       {'systemName': system['name']}, 
                       local)
      for station in data_stations['stations']:
        controlling_faction = None
        if 'controllingFaction' in station:
          controlling_faction = station['controllingFaction']['name']
        values = [systemName,station['name'],station['type'],station['distanceToArrival'],station['economy'],controlling_faction]
        try:
          c.execute("INSERT INTO Stations VALUES (?,?,?,?,?,?)",values)
        except sqlite3.IntegrityError:
          pass
      debug("Updating system: {0}".format(system['name']))
      fetch_system_factions(data_system['name'], local)
  conn.commit()
 
def fetch_system_factions(systemName, local = False):
  conn = get_db_connection()
  c = conn.cursor()
  data_factions = get_json_data("factions_{0}.json".format(systemName),
                       "https://www.edsm.net/api-system-v1/factions",
                       {'systemName': systemName, 'showHistory':1}, 
                       local)
  if not data_factions['factions']:
    return None
  for faction in data_factions['factions']:
    if not fetch_faction(faction['name']):
      values = [faction['name'],faction['allegiance'],faction['government'],faction['isPlayer'], None]
      c.execute("INSERT INTO Factions VALUES (?,?,?,?,?)",values)
  conn.commit()
 
def update_tick2(cur_time = None, local = False, history = False,forced=False):
  current_time = get_timestamp(cur_time)
  c = conn.cursor()
  if not forced:
    if not is_update_needed(current_time) and not history:
      debug("UPDATE NOT NEEDED")
      return False
    else:
      debug("UPDATE NEEDED")
  else:
    debug("UPDATE FORCED")
  if not history:
    print("update TICK")
    c.execute("INSERT INTO ticks VALUES (?)",[current_time])
  star_systems = get_systems("population > 0 ORDER BY population")
  total_systems = len(star_systems)
  print(total_systems)
  current_start_system = 1
  for star_system in star_systems:
    systemName = star_system[0]
    system_info = update_system(systemName)['information']
    sys.stdout.write("Updating System {0} [{1}/{2}]           \r".format(systemName,current_start_system,total_systems))
    current_start_system += 1
    sys.stdout.flush()
    values = [current_time,systemName,system_info['faction'],system_info['security']]
    if not history:
      c.execute("INSERT INTO system_status VALUES (?,?,?,?)",values)
    
    data_factions = get_json_data("factions_{0}.json".format(systemName),
                         "https://www.edsm.net/api-system-v1/factions",
                         {'systemName': systemName,'showHistory':1}, 
                         local)
    if not data_factions['factions']:
      return False
    for faction in data_factions['factions']:
      system_faction_entries = []
      active_state_entries = []
      pending_state_entries = []
      recovering_state_entries = []  
      if history:
        for timestamp in faction['stateHistory']:
          c.execute("INSERT INTO ticks VALUES (?)",[int(timestamp)])
          state = faction['stateHistory'][timestamp]
          active_state_entries.append([int(timestamp),state,'activeState',faction['name'],0])
          #print(timestamp,state)
        for timestamp in faction['influenceHistory']:
          c.execute("INSERT INTO ticks VALUES (?)",[int(timestamp)])
          system_faction_entries.append([int(timestamp),
            faction['name'],
            systemName,
            faction['influenceHistory'][timestamp]])
        if faction['recoveringStatesHistory']:
          for timestamp,state in faction['recoveringStatesHistory'].items():
            c.execute("INSERT INTO ticks VALUES (?)",[int(timestamp)])
            if not state:
              state = {'state': "None",'trend':0}
            else:
              state = state[0]
            recovering_state_entries.append([int(timestamp),
                                  state['state'],
                                  "recoveringState",
                                  faction['name'],
                                  state['trend']])
        if faction['pendingStatesHistory']:
          for timestamp,state in faction['pendingStatesHistory'].items():
            if not state:
              continue
            c.execute("INSERT INTO ticks VALUES (?)",[int(timestamp)])
            state = state[0]
            pending_state_entries.append([int(timestamp),
                                  state['state'],
                                  "pendingState",
                                  faction['name'],
                                  state['trend']])
      system_faction_entries.append([current_time,
                                      faction['name'],
                                      systemName,
                                      faction['influence']])
      active_state_entries.append([current_time,faction['state'],'activeState',faction['name'],0])
      for state in faction['recoveringStates']:
        pending_state_entries.append([current_time,
                              state['state'],
                              "recoveringState",
                              faction['name'],
                              state['trend']])
      for state in faction['pendingStates']:
        recovering_state_entries.append([current_time,
                              state['state'],
                              "pendingState",
                              faction['name'],
                              state['trend']])
      for values in system_faction_entries:
        if history:
          check_query = """
          SELECT * FROM faction_system WHERE
          date={0} AND
          name="{1}" AND
          influence={3}""".format(*values)
          c.execute(check_query)
          if c.fetchone():
            #debug("ENTRY_ALREADY_EXISTS")
            continue
        try: 
          c.execute("INSERT INTO faction_system VALUES (?,?,?,?)",values)
        except sqlite3.IntegrityError:
          continue
      for values in active_state_entries:
        try:
          c.execute("INSERT INTO faction_state VALUES (?,?,?,?,?)",values)
        except sqlite3.IntegrityError:
          continue
      for values in pending_state_entries:
        try:
          c.execute("INSERT INTO faction_state VALUES (?,?,?,?,?)",values)
        except sqlite3.IntegrityError:
          continue
      for values in recovering_state_entries:
        try:
          c.execute("INSERT INTO faction_state VALUES (?,?,?,?,?)",values)
        except sqlite3.IntegrityError:
          continue
        
      if history:  
        conn.commit()
  conn.commit()
  return True
 
def default_expansion_filter(systems,target):
  expansion_systems= [exp_system for exp_system in systems if (exp_system == target) or (len(System(exp_system).get_factions()) < 7)]
  return expansion_systems

def get_next_target(origin,target,expansion_filter=default_expansion_filter):
  systems = [sys[0] for sys in get_systems()]
  path = [origin]
  found = False
  current = origin
  systems.remove(origin)
  while not found:
    closest = System(current).get_closest_systems()
    closest_list =  [valid["system"] for valid in closest if valid["system"] not in path]
    closest_list = expansion_filter(closest_list,target)
    closest_list = [valid_system for valid_system in closest_list if (valid_system in systems) or (valid_system == target)]
    current = closest_list[0]
    if(current == target):
      path.append(current)
      found = True
    else:
      path.append(current)
      systems.remove(current)
  return path

if 0:
  if not IS_FLASK_ENVIRONMENT:
    conn = sqlite3.connect(DATABASE)
    print(get_next_target("Naunin", "Belanit"))
    conn.close()
    exit(0) 

if 0:
  conn = sqlite3.connect(DATABASE)
  
  #fetch_bubble("Naunin")
  #fetch_bubble("Smethells 1")
  #clean_updates()
  #update_tick2()
  result =[]
  star_system = System("Juipek")
  system_factions = star_system.get_current_factions()
  for faction in system_factions:
    f = Faction(faction)
    print(f)
    if f:
      state = f.get_state()
      influence = f.get_current_influence_in_system(star_system)
      if state and influence:
        faction_dict = {"name":faction,"state":state,"influence":"{0:.2f}".format(influence*100.0)}
        result.append(faction_dict)
  get_days(1527852431,1517745656)
  print(get_last_update())
  
  
  g = Faction("Fathers of Nontime")
  for timestamp, influence in g.get_influence_in_system("Naunin", start_timestamp=0):
    print(get_date_from_epoch(timestamp),influence)
  for timestamp, state_type, state in g.get_states(state_type="activeState", start_timestamp=0):
    print(get_date_from_epoch(timestamp),state,state_type)
  conn.close()

#create_database()
#fresh_hard_update()
if __name__ == "__main__":
  #fresh_hard_update(history=True)
  update_tick()
  f = Faction(FACTION_CONTROLLED)
  print(get_next_target("Naunin", "Superty"))

