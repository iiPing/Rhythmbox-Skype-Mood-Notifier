#    Rhythmbox Skype Mood Notifier - updates skype mood text from playlist
#    Copyright (C) 2007 Christopher Gabijan
#    Copyright (C) 2008 Christopher Gabijan ????? still ???? \(^_^)_ 
#    Copyright (C) 2009 Christopher Gabijan ????? come-on ~(*_*)~
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop


class DBusSkype:
  def __init__(self):
    DBusGMainLoop(set_as_default=True)
    self.bus = dbus.SessionBus()
    self.reconnect()

  def reconnect(self):
    try:
       self.skype_api = self.bus.get_object('com.Skype.API', '/com/Skype')
    except:
       pass

    if(self.skype_api):
      ans = self.skype_api.Invoke('Name RhythmBox-Mood-Notifier')
      if (ans == 'OK'):
        self.is_connected = True
      else :
        self.is_connected = False

      ans = self.skype_api.Invoke('PROTOCOL 5')
      if (ans == 'PROTOCOL 5'):
        self.is_supported = True
      else :
        self.is_supported = False

  def setStatus(self,mood_message):
    self.reconnect()
    if (self.is_connected and self.is_supported):
      self.skype_api.Invoke('SET PROFILE RICH_MOOD_TEXT %s' % str(mood_message))

  def getStatus(self):
    self.reconnect()
    curr_mood_msg = ''
    if(self.is_connected and self.is_supported):
      curr_mood_msg = self.skype_api.Invoke('GET PROFILE RICH_MOOD_TEXT')
      if curr_mood_msg.startswith('GET PROFILE RICH_MOOD_TEXT') :
        tmp = curr_mood_msg[27:]
        curr_mood_msg = tmp
      elif curr_mood_msg.startswith('PROFILE RICH_MOOD_TEXT') :
        tmp = curr_mood_msg[23:]
        curr_mood_msg = tmp
    return str(curr_mood_msg)

