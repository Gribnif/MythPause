MythPause is a Python script which solves several prominent problems with
MythTV:

Scenario 1:

  You're watching a program in the living room, and it's dinner time. You want
  to continue the program on the frontend in the kitchen, but getting back to
  the exact program and location you were just watching takes a lot of button
  presses on the remote.

  MythPause will let you create a single key press on your remote control which
  saves the position and stops the frontend then, when you use your remote on
  the second frontend, the same key press resumes playback at the exact
  location you were just viewing.

Scenario 2:

  Your kids want to watch the same parts of their favorite movies--not the
  whole thing--over, and over, and over. You could use the bookmark feature,
  but that still means having to find the movie. You also can't store more than
  one bookmark per movie.

  With MythPause, you can set up any number of bookmarks that, when activated,
  resume playback at the chosen location with a single command. They can even
  be added to a menu inside the frontend, to make it easy for the kids to use.

Scenario 3:

  You use MythTV's bookmark feature to save the start of programs that get
  viewed over and over. So, what if you're in the middle of watching and want
  to continue watching where you left off? If you save the traditional
  bookmark, finding the program start will be difficult the next time you want
  to start over.

  MythPause saves its positions into its own part of the database, so you can
  use it without affecting the built-in bookmark.

Scenario 4:

  You're looking for another way to drill down to some of the harder to reach
  jump points, like Weather or Images, using a remote control key press.

  You can do that, too, using MythPause!


Requirements:

- MythTV Python bindings, version 0.25. This script may work with 0.24 or 0.26,
  but these versions are untested.
- The "argparse" module, which is included with Python 2.7 or newer. If you use
  an older verison of Python, it can be installed using the "python-argparse"
  package (with yum, apt-get, etc.), or with "sudo easy_install argparse".
- The frontend's network control socket must be enabled. See this page for more
  information:  http://www.mythtv.org/docs/mythtv-HOWTO-11.html#ss11.5


Typical setup:

  1. Figure out what user runs mythfrontend, and copy the script somewhere so
     that user can run it. For example:

     $ ps auxw | grep mythfrontend
     $ sudo cp MythPause.py /usr/local/share/mythtv

  2. Make the script executable:

     $ sudo chmod 755 /usr/local/share/mythtv/MythPause.py


Calling from the command line:

  There are lots of options in MythPause, to make it very flexible. But, of
  course, that can also make it more complex to use:

  MythPause.py [-h] [-i ID] [-x] [-c] [-d] [-v]
               [-s | -r | -t | -p | -g VALUE | -G | -S VALUE | -C ID | -a]

  All arguments are optional, however you must supply at least one action from
  the second line.

  Optional arguments:

  -h, --help
      Show a help message and exit.

  -i ID, --id ID
      Set the unique identifier for the saved/resumed position. If no ID is
      supplied, the ID ".default" is used.

      This option allows you to permanently save multiple locations. The ID you
      supply is limited to alphanumeric characters, underscore, and hyphen; any
      other characters are removed. If your MythTV database is case-sensitive,
      then the ID will be, too (but the default for MySQL databases is not
      case-sensitive.)

  -x, --stop
      Stop playback. This can be combined with other actions, such as --save,
      or --current.

  -c, --clear
      Clear saved position (not valid with --save, --toggle, --set or
      --clear-all.)

  -d, --debug
      Don't actually write changes or alter the frontend's behavior; assumes
      --verbose

  -v, --verbose
      Give verbose output.

  Frontend connection:

  -H HOSTNAME, --host HOSTNAME
      Hostname of frontend (defaults to value from config file)

  -P PORT, --port PORT
      Port number of frontend socket (defaults to 6546)

  Actions; at least one of these is required:

  -s, --save
      Save position, using the given --id or ".default". This command can be
      combined with --stop to stop playback, among other options. If playback
      is currently paused, this fact is not saved; when resuming, playback will
      restart automatically. These types of information can be saved:

      Playback of recordings: program, position, speed
      Playback of videos: file name, position, speed
      Live TV: channel
      Other menu locations

  -r, --resume
      Restore the previously saved position, using the given --id or
      ".default". This command can be combined with --clear to clear the
      bookmark, among other options.

  -t, --toggle
      If the position is not yet saved, save it and stop playback; otherwise,
      resume at the saved location. It is useful to include --clear with this
      command, to clear the saved value after resuming (--clear has no effect
      if the position is not yet saved.)

  -p, --current
      Print the frontend's current position. The printed string can be used
      later on with --set or --go.

  -g VALUE, --go VALUE
      Go to the given location, using the output from --get or --current.
      Remember that you may have to enclose the string in quotes, to keep
      spaces and other characters from being interpreted by the shell.

  -G, --get
      Get and print a saved position, using the given --id or ".default".

  -S VALUE, --set VALUE
      Save a position, using the output from --get or --current. Remember that
      you may have to enclose the string in quotes, to keep spaces and other
      characters from being interpreted by the shell.

  -C NEW_ID, --copy-to NEW_ID
      Copy a previously saved position to a new slot using NEW_ID. The source
      of the copy is either the value of --id, or ".default".

  -a, --clear-all
      Clear all saved positions


Examples:

  I. Create a series of bookmarks to commonly-viewed programs:

    1. Start playback of the first program to be saved.
    2. Move to the desired position. Pause playback, to make the saved position
       more accurate.
    3. Call the script:
       $ MythPause.py --id Bookmark1 --save
    4. Repeat steps 1-3 for the remaining programs, using a different value for
       --id.
    5. You can resume using a bookmark with a command like this:
       $ MythPause.py --id Bookmark1 --resume
    6. You can optionally tie these commands to menu entries by creating a copy
       of the XML files that make up the menu structure. See this page for more
       details:

       http://www.mythtv.org/wiki/Menu_theme_development_guide

       If you would like to run these commands from buttons on your remote
       control, see the section below on using LIRC's irexec.

  II. Create a single command that is assigned to a button and pauses/resumes
      playback at the current location:

    Simply use this command:

      $ MythPause.py --toggle --clear

    To run it from a button on your remote control, see the section below on
    using LIRC's irexec.

  III. Custom Jump Points:

    1. Go to a place in the frontend menus you would like to be able to return
       to easily.
    2. Either use the method described in Example I, above, to save the
       locations using named bookmarks, or use:

      $ MythPause.py --current

      to see what value to use for the current menu, then use the --go command
      whenever you want to return to that location. For instance, if you were
      at the Watch Videos screen, you would get:

      $ MythPause.py --current
      mythvideo

      Which means you would use this command to return there later on:

      $ MythPause.py --go mythvideo

      Remember that you may have to enclose the argument to --go in quotes, to
      keep spaces and other characters from being interpreted by the shell.


Using with LIRC's irexec:

  To call this script from a remote control key press, you should consider
  using the irexec program that comes with LIRC. For each key press, add a new
  section to ~/.mythtv/lircrc, with the line "prog = irexec". Here is an
  example:

  begin
    prog = irexec
    button = dvd273-p12
    config = python /usr/local/share/mythtv/MythPause.py -i Toggle --toggle
    --clear -H tiny2
  end

  The "button =" line defines the button press which will activate the command.
  The easiest way to figure this out is to use the command "irw".

  The "config =" line defines the program to run. In this case, MythPause.py is
  being passed as an argument to "python", in case it is not executable. The
  remainder of the command line is passed to MythPause.py, and tells it to:

    - use an id of "Toggle" (-i)
    - toggle save/resume (--toggle)
    - clear the saved state, if it's being restored (--clear)
    - use the frontend on host "tiny2" (-H)

  For more information on common problems when using irexec, see:

    http://www.linuxquestions.org/questions/linux-software-2/
      execute-script-with-irexec-from-mythtv-629861/


Known Bugs and Limitations:

  - There is a known bug in current (as of 9/1/12) versions of MythTV regarding
    playback of recorded programs from the network control socket used by this
    script.

    If you have set the option to ask whether or not to save the traditional
    bookmark upon exiting a recording, it is ignored when exiting a recording
    that was started with the control socket. This bug does not affect videos.
    See this page for more information:

    http://code.mythtv.org/trac/ticket/11055

  - Whenever a program asks a frontend to stop playback using the documented
    command, the traditional bookmark is saved. This is a bad thing if you want
    the bookmark to remain unaltered, so that you can always start at that
    place in the recording.

    Therefore, when this script's --stop or --toggle option is used, it sends a
    keystroke to the frontend, as though the Escape key on a keyboard had been
    pressed. This is the default key for exiting a recording, but if you have
    redefined it, playback will not stop.

    Also, if you have enabled the prompt to ask whether to save the bookmark
    when stopping, the prompt will appear. This can be confusing when using the
    --toggle command, since the prompt asks you to save a "bookmark", which is
    different from the type of bookmark provided by this script. When using
    --toggle, you should answer "Do not save, just exit to the menu".
