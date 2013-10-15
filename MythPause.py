#  MythPause.py
#  Copyright 2013 Dan Wilga
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import re
import json
import httplib
import urllib
import time

try:
  import argparse
except:
  sys.exit('The Python argparse module is required. Try installing the "python-argparse" package, or using "easy_install argparse".')

mode_error = 'At least one of --save (-s), --resume (-r), --toggle (-t), --swap (-w), --current (-p), --go (-g), --get (-G), --set (-S), --copy-to (-C), --stop (-x), or --clear (-c) is required.';
parser = argparse.ArgumentParser(description='Save the current MythTV playback location for future resumption, either on this frontend or another. The positions of recordings, videos, live TV, and certain jump points can be saved.', epilog=mode_error)
parser.add_argument('-i', '--id', default='.default', help='unique identifier for the saved/resumed position')
group = parser.add_mutually_exclusive_group()
group.add_argument('-s', '--save', action='store_true', help='save position')
group.add_argument('-r', '--resume', action='store_true', help='restore previously saved position')
group.add_argument('-t', '--toggle', action='store_true', help='if the position is not yet saved, save it and stop playback; otherwise, resume the saved state')
group.add_argument('-w', '--swap', action='store_true', help='swap the current position with the saved state')
group.add_argument('-p', '--current', action='store_true', help="print the frontend's current position")
group.add_argument('-g', '--go', metavar='VALUE', help='go to the given location, using the output from --get or --current')
group.add_argument('-G', '--get', action='store_true', help='get and print a saved position')
group.add_argument('-S', '--set', metavar='VALUE', help='save a position, using the output from --get or --current')
group.add_argument('-C', '--copy-to', metavar='NEW_ID', help='copy previously saved position to a new slot using NEW_ID')
parser.add_argument('-x', '--stop', action='store_true', help='stop playback')
parser.add_argument('-c', '--clear', action='store_true', help='clear saved position (not valid with --save, --toggle, or --set)')
parser.add_argument('-F', '--frontend', default='localhost', metavar='HOSTNAME', help='hostname of frontend (defaults to localhost)')
parser.add_argument('-f', '--frontend-port', default=6547, metavar='PORT', help='port number of frontend socket (defaults to 6547)')
parser.add_argument('-B', '--backend', default='localhost', metavar='HOSTNAME', help='hostname of backend (defaults to localhost)')
parser.add_argument('-b', '--backend-port', default=6544, metavar='PORT', help='port number of backend socket (defaults to 6544)')
parser.add_argument('-d', '--debug', action='store_true', help="don't actually write changes or alter the frontend's behavior; assumes --verbose")
parser.add_argument('-v', '--verbose', action='store_true', help='verbose output')

global args, fe, db, var_name, kClearSettingValue
fe = be = None
kClearSettingValue = "<clear_setting_value>"    # from libs/libmythbase/mythdb.cpp

args = parser.parse_args()

#--------------------------------------
def verbose(val):
  if args.verbose or args.debug:
    print val

# Read a saved location from the database
def get_saved(exit_on_err = False):
  global var_name
  be = open_be()
  data = http_get(be, '/Myth/GetSetting?Key=' + urllib.quote(var_name))
  if data is None or 'SettingList' not in data or 'Settings' not in data['SettingList'] or var_name not in data['SettingList']['Settings'] or data['SettingList']['Settings'][var_name] == '':
    if exit_on_err:
      sys.exit('There is no saved state with id = {0}'.format(args.id))
    return None
  return data['SettingList']['Settings'][var_name]

# Query the current location from the frontend
def get_current():
  if not hasattr(get_current, "last_location"):
    fe = open_fe()
    status_resp = http_get(fe, '/Frontend/GetStatus')
    verbose('Status_resp = {0}'.format(status_resp))
    if 'currentlocation' in status_resp['FrontendStatus']['State']:
      xlate = {
        'playbackbox' : 'TV Recording Playback',
        'mythvideo' : 'Video Default',
        'mainmenu' : 'Main Menu',
        'mythgallery' : 'MythGallery',
        'GameUI' : 'MythGame',
        'mythnews' : 'MythNews',
        'guidegrid' : 'Program Guide',
        'ViewScheduled' : 'VIEWSCHEDULED',
      }
      location = status_resp['FrontendStatus']['State']['currentlocation']
      verbose('Location = {0}'.format(location))
      if location not in xlate:
        sys.exit('Unknown location {0}'.format(location))
      location = 'SendAction?Action=' + urllib.quote(xlate[location])
    else:
      location = status_resp['FrontendStatus']['State']['state']
      if location == 'WatchingVideo':
        location = 'PlayVideo?Id=' + status_resp['FrontendStatus']['State']['programid'] + '|pause|SendAction?Action=SEEKABSOLUTE&Value=' + status_resp['FrontendStatus']['State']['secondsplayed']
      elif location == 'WatchingPreRecorded':
        location = 'PlayRecording?ChanId=' + status_resp['FrontendStatus']['State']['chanid'] + '&StartTime=' + status_resp['FrontendStatus']['State']['starttime'] + '|pause|SendAction?Action=SEEKABSOLUTE&Value=' + status_resp['FrontendStatus']['State']['secondsplayed']
    verbose('Current location = {0}'.format(location))
    get_current.last_location = location
  return get_current.last_location

# Save a location to the database
def save(data, to_var_name = None):
  if to_var_name is None:
    global var_name
    to_var_name = var_name
  be = open_be()
  if args.debug:
    verbose('Would have saved: {0}'.format(data))
    return
  http_post(be, '/Myth/PutSetting', {'Key' : to_var_name, 'Value' : data})
  verbose('Saved: {0}'.format(data))

# Resume at a previously saved location
def resume(location):
  verbose('Resuming playback using location = {0}'.format(location))
  cmds = location.split('|')
  for str in cmds:
    if str == 'pause':
      verbose('Pausing')
      time.sleep(0.5)
    elif args.debug:
      verbose('Would have sent {0}'.format(str))
    else:
      fe = open_fe()
      verbose('Sending {0}'.format(str))
      http_get(fe, '/Frontend/' + str)

# If --stop is set, stop playback
def cond_stop():
  if args.stop:
    stop()

# Stop playback
def stop():
  fe = open_fe()
  verbose('Stopping playback')
  if args.debug:
    verbose('Would have stopped')
  else:
    http_get(fe, '/Frontend/SendAction?Action=STOPPLAYBACK')

# If --clear is set, clear the saved location
def cond_clear():
  if args.clear:
    clear()

# Clear the saved location
def clear():
  global var_name, kClearSettingValue
  verbose('Clearing saved position for {0}'.format(var_name))
  be = open_be()
  if args.debug:
    verbose('Would have cleared the saved position for {0}'.format(var_name))
  else:
    http_post(be, '/Myth/PutSetting', {'Key' : var_name, 'Value' : kClearSettingValue})

# Convert an id to a settings variable name
def get_var_name(id):
  # .default is unique
  if id == '.default':
    new_name = 'MythPause_.default'
  else:
    patt = re.compile(r'[^a-z0-9_-]', flags=re.I)
    new_name = 'MythPause_' + re.sub(patt, '', id)
  verbose('var_name = {0}'.format(new_name))
  return new_name

# Open a frontend connection
def open_fe():
  global fe
  if fe is not None:
    close_fe()
  verbose('Opening frontend connection using {0}:{1}'.format(args.frontend, args.frontend_port))
  fe = httplib.HTTPConnection(args.frontend, args.frontend_port)
  return fe

# Close frontend connection
def close_fe():
  global fe
  if fe is not None:
    fe.close()
    fe = None

# Open a backend connection
def open_be():
  global be
  if be is not None:
    close_be()
  verbose('Opening backend connection using {0}:{1}'.format(args.backend, args.backend_port))
  be = httplib.HTTPConnection(args.backend, args.backend_port)
  return be

# Close backend connection
def close_be():
  global be
  if be is not None:
    be.close()
    be = None

# Use GET to contact the frontend or backend
def http_get(conn, request):
  verbose('GET ' + request)
  conn.request('GET', request, headers={'Accept': 'text/javascript'})
  r = conn.getresponse()
  result = r.read()
  if r.status == 200:
    verbose('Response: ' + result)
    return json.loads(result)

# Use POST to contact the frontend or backend
def http_post(conn, url, data):
  data = urllib.urlencode(data)
  verbose('POST ' + url + ' ' + data)
  conn.request('POST', url, data, {'Accept': 'text/javascript', 'Content-type' : 'application/x-www-form-urlencoded'})
  r = conn.getresponse()
  if r.status == 200:
    return json.loads(r.read())
  verbose('Response: {0} {1}'.format(r.status, r.reason))

#--------------------------------------
var_name = get_var_name(args.id)
acted = False

if args.save:
  save(get_current())
  cond_stop()
  acted = True
elif args.resume:
  resume(get_saved(True))
  cond_clear()
  cond_stop()
  acted = True
elif args.go:
  resume(args.go)
  acted = True
elif args.toggle:
  data = get_saved()
  if data is None:
    save(get_current())
    stop()
  else:
    resume(data)
    cond_clear()
  acted = True
elif args.swap:
  data = get_saved()
  current = get_current()
  if data is None:
    verbose('No previous saved position')
    stop()
  else:
    resume(data)
  save(current)
  acted = True
elif args.current:
  print get_current()
  cond_stop()
  acted = True
elif args.get:
  print get_saved(True)
  cond_clear()
  cond_stop()
  acted = True
elif args.set:
  save(args.set)
  cond_stop()
  acted = True
elif args.copy_to:
  save(get_saved(True), get_var_name(args.copy_to))
  cond_clear()
  cond_stop()
  acted = True
else:
  if args.clear:
    cond_clear()
    acted = True
  if args.stop:
    stop()
    acted = True

if not acted:
  sys.exit(mode_error)
