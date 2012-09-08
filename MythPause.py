import sys
import re

try:
  import argparse
except:
  sys.exit('The Python argparse module is required. Try installing the "python-argparse" package, or using "easy_install argparse".')

mode_error = 'At least one of --save (-s), --resume (-r), --toggle (-t), --current (-p), --go (-g), --get (-G), --set (-S), --copy-to (-C), --clear-all (-a), --stop (-x), or --clear (-c) is required.';
parser = argparse.ArgumentParser(description='Save the current MythTV playback location for future resumption, either on this frontend or another. The positions of recordings, videos, live TV, and certain jump points can be saved.', epilog=mode_error)
parser.add_argument('-i', '--id', default='.default', help='unique identifier for the saved/resumed position')
group = parser.add_mutually_exclusive_group()
group.add_argument('-s', '--save', action='store_true', help='save position')
group.add_argument('-r', '--resume', action='store_true', help='restore previously saved position')
group.add_argument('-t', '--toggle', action='store_true', help='if the position is not yet saved, save it and stop playback; otherwise, resume the saved state')
group.add_argument('-p', '--current', action='store_true', help="print the frontend's current position")
group.add_argument('-g', '--go', metavar='VALUE', help='go to the given location, using the output from --get or --current')
group.add_argument('-G', '--get', action='store_true', help='get and print a saved position')
group.add_argument('-S', '--set', metavar='VALUE', help='save a position, using the output from --get or --current')
group.add_argument('-C', '--copy-to', metavar='NEW_ID', help='copy previously saved position to a new slot using NEW_ID')
group.add_argument('-a', '--clear-all', action='store_true', help='clear all saved positions')
parser.add_argument('-x', '--stop', action='store_true', help='stop playback')
parser.add_argument('-c', '--clear', action='store_true', help='clear saved position (not valid with --save, --toggle, --set or --clear-all)')
parser.add_argument('-H', '--host', metavar='HOSTNAME', help='Hostname of frontend (defaults to value from config file)')
parser.add_argument('-P', '--port', metavar='PORT', help='Port number of frontend socket (defaults to 6546)')
parser.add_argument('-d', '--debug', action='store_true', help="don't actually write changes or alter the frontend's behavior; assumes --verbose")
parser.add_argument('-v', '--verbose', action='store_true', help='verbose output')
#host/port/username/password

global args, fe, db, var_name
fe = db = None

args = parser.parse_args()

#--------------------------------------
def verbose(val):
  if args.verbose or args.debug:
    print val

# Read a saved location from the database
def get_saved(exit_on_err = False):
  global var_name
  db = open_db()
  data = db.settings.NULL[var_name];
  if exit_on_err and data is None:
    sys.exit('There is no saved state with id = {0}'.format(args.id))
  return data

# Query the current location from the frontend
def get_current():
  if not hasattr(get_current, "last_location"):
    fe = open_fe()
    location = fe.sendQuery('location')
    verbose('Location = {0}'.format(location))
    if location in set(['visualizerview', 'searchview', 'playlisteditorview', 'playlistview']):
      location = 'playmusic'
    else:
      matches = re.match(r'Playback (Recorded|LiveTV) (\d\d?:\d\d(?::\d\d)?) of \S+ ([\d\.]+x|pause) (\d+) (\d\d\d\d-\d\d-\d\dT\d\d:\d\d:\d\d) ', location)
      if matches:
        if matches.group(1) == 'Recorded':
          location = 'recorded|program ' + matches.group(4) + ' ' + matches.group(5) + '|seek ' + fix_seek(matches.group(2)) + fix_speed(matches.group(3));
        else:
          location = 'livetv|chanid ' + matches.group(4)
      else:
        matches = re.match(r'Playback Video (\d\d?:\d\d(?::\d\d)?) ([\d\.]+x) (.*?) \d+ [\d\.]+$', location)
        if matches:
          location = 'video|file ' + matches.group(3) + '|seek ' + fix_seek(matches.group(1)) + fix_speed(matches.group(2))
    verbose('Current location = {0}'.format(location))
    get_current.last_location = location
  return get_current.last_location

# Save a location to the database
def save(data, to_var_name = None):
  if to_var_name is None:
    to_var_name = var_name
  db = open_db()
  if args.debug:
    verbose('Would have saved: {0}'.format(data))
    return
  with db as cursor:
    cursor.execute("DELETE FROM settings WHERE `value` = '{0}'".format(to_var_name))
    cursor.execute("INSERT INTO settings (`value`,data,hostname) VALUES('{0}', '{1}', NULL)".format(to_var_name, data))
  verbose('Saved: {0}'.format(data))

# Resume at a previously saved location
def resume(location):
  verbose('Resuming playback using location = {0}'.format(location))
  fe = open_fe()
  cmds = location.split('|')
  mode = cmds.pop(0)
  if mode == 'livetv':
    fe.jump.livetv
  elif len(cmds) == 0:
    fe.jump[mode]
  else:
    for str in cmds:
      if args.debug:
        verbose('Would have sent {0}'.format(str))
      else:
        verbose('Sending {0}'.format(str))
        fe.sendPlay(str)

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
    # Annoyingly, if a recording is playing and is told to stop, it saves the
    # traditional bookmark without asking. This can be undesired, so instead
    # send the Escape keypress, which might not work, either, depending on the
    # settings.
    fe.key.escape
    # If you don't mind the bookmark being set, you can use this instead:
##    fe.sendPlay('stop')

# If --clear is set, clear the saved location
def cond_clear():
  if args.clear:
    clear()

# Clear the saved location
def clear():
  global var_name
  verbose('Clearing saved position for {0}'.format(var_name))
  db = open_db()
  if args.debug:
    verbose('Would have cleared the saved position for {0}'.format(var_name))
  else:
    with db as cursor:
      cursor.execute("DELETE FROM settings WHERE `value` = '{0}'".format(var_name))

# Clear all saved locations
def clear_all():
  verbose('Clearing all saved positions')
  db = open_db()
  if args.debug:
    verbose('Would have cleared all saved positions')
  else:
    with db as cursor:
      cursor.execute("DELETE FROM settings WHERE `value` LIKE 'MythPause%'")

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
  if fe is None:
    from MythTV import Frontend
    port = 6546
    if args.port:
      port = args.port
    if args.host:
      verbose('Opening frontend connection using {0}:{1}'.format(args.host, port))
      fe = Frontend(args.host, port)
    else:
      verbose('Opening frontend connection using defaults')
      fe = Frontend.fromUPNP().next()
  return fe

# Open a database connection
def open_db():
  global db
  if db is None:
    from MythTV import MythDB
    verbose('Opening database connection')
    db = MythDB()
  return db

# Convert short seek locations to the HH:MM:SS format expected for playback
def fix_seek(seek):
  old_seek = seek
  if len(seek) == 4:
    seek = '00:0' + seek
  elif len(seek) == 5:
    seek = '00:' + seek
  elif len(seek) == 7:
    seek = '0' + seek

  if seek != old_seek:
    verbose('Adjusted seek position {0} => {1}'.format(old_seek, seek))
  return seek

def fix_speed(speed):
  if speed[-1] == 'x':
    return '|speed ' + speed
  verbose('Omitting speed, because playback is paused')
  return ''

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
elif args.clear_all:
  clear_all()
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
