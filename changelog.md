# Version 1.2
 - Add docstrings to messages.py.
 - Changed repr of Message.
 - Added WhisperMessage.
 - Added a scheduler to Bot.
 - Added matcher_function field to Command.
 - Fixed a bug in Connection.__init__ not registering the atexit close handler. 
 - Changed regexes.
# Version 1.1
 - changed version number to 1.1,
 - added required_permissions to Bot.add_command,
 - fixed a minor comment mistake (Bot line 129),
 - changed Bot.send() to automatically pick the queue,
 - changed docstrings in connection.py,
 - tweaked some regexps,
 - added the GlobalNoticeMessage and UsernoticeMessage classes (UsernoticeMessage has not pattern attached to it),
 - removed some commented-out code,
 - added `__dict__` to PermissionList,
 - changed all stock commands to use the required_permissions argument in bot.add_command, instead of twitchirc.require_permission