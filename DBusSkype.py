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

import gtk
import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop


SKYPE_API_NAME = 'com.Skype.API'
SKYPE_API_PATH = '/com/Skype'
SKYPE_CLIENT_PATH = '/com/Skype/Client'
PLUGIN_NAME = 'RhythmBox-Mood-Notifier'


SKYPE_CMD_DICT = {
  'Connect' : 'Name',
  'Prot5':'PROTOCOL 5',
  'SetMood':'SET PROFILE RICH_MOOD_TEXT',
  'GetMood':'GET PROFILE RICH_MOOD_TEXT'
}

SKYPE_CALL_BEGIN = ["EARLYMEDIA","RINGING","ROUTING"]
SKYPE_CALL_END   = ["BUSY","CANCELLED","REFUSED","FINISHED","MISSED","FAILED"]

'''
Exported Object carries Skype notify method / function
'''
class ExpObjSkypeListener(dbus.service.Object):
    def __init__(self, bus, aCallBackMethod):
        dbus.service.Object.__init__(self, bus, SKYPE_CLIENT_PATH)
        self.cbMethod = aCallBackMethod


    @dbus.service.method(dbus_interface='com.Skype.API.Client')
    def Notify(self, commandStr):
        self.cbMethod(unicode(commandStr))

    def deAttach(self):
      self.cbMethod = None
      self.remove_from_connection()


class SkypeRhythmboxMediator():
  ''' a mediator for skype and rhythmbox 
  '''

  def __init__(self,cbmRBPause,cbmRBPlay,cbmRBIsPlaying,pauseMessage='(music - paused)'):
    DBusGMainLoop(set_as_default=True)
    self.bus = None
    self.RBPause = cbmRBPause
    self.RBPlay = cbmRBPlay
    self.RBIsPlaying  = cbmRBIsPlaying

    self.rbWasPlaying = False
    self.oldSongTitle = None
    self.skype_api = None
    self.skype_listener = None
    self.connected = False
    self.protSupported = False
    self.pauseMessage = pauseMessage

  def hook(self):
    self.bus = dbus.SessionBus()
    self.skype_stat = self.bus.add_signal_receiver(
             self.SKLoginLogout,
             'NameOwnerChanged',
             'org.freedesktop.DBus',
             'org.freedesktop.DBus',
             '/org/freedesktop/DBus',
             arg0=SKYPE_API_NAME)
    self.cleanRef()
    self.connect()
    

  def connect(self):
    if self.isSkypeRunning() :
      try :
        self.skype_api = self.bus.get_object(SKYPE_API_NAME,SKYPE_API_PATH)
        ans = self.skype_api.Invoke('%s %s' % (SKYPE_CMD_DICT.get('Connect'),PLUGIN_NAME))
        if (ans == 'OK'): self.connected = True
        ans = self.skype_api.Invoke('%s' % SKYPE_CMD_DICT.get('Prot5'))
        if (ans == SKYPE_CMD_DICT.get('Prot5')): self.protSupported = True
        self.skype_listener = ExpObjSkypeListener(self.bus,self.SKNotifyListener)

      except:
        pass

  def cleanRef(self):
    if self.skype_api : self.skype_api = None
    if self.skype_listener : 
      self.skype_listener.deAttach()
      self.skype_listener = None
    self.connected = False
    self.protSupported = False



  def SKNotifyListener(self, cmdStr):
    if cmdStr.startswith('CALL'):
      cmdStrArr = cmdStr.split()
      if (len(cmdStrArr) == 4 and cmdStrArr[2] == 'STATUS'):
        gtk.gdk.threads_enter()
        if (cmdStrArr[3] in SKYPE_CALL_BEGIN) :
          if self.RBIsPlaying() :
            self.rbWasPlaying = True
            self.RBPause()
            self.oldSongTitle = self.SKGetMood()
            self.SKSetMood(self.pauseMessage)
        elif (cmdStrArr[3] in SKYPE_CALL_END) :
          if self.rbWasPlaying :
            self.rbWasPlaying  = False
            if self.oldSongTitle : self.SKSetMood(self.oldSongTitle)
            self.RBPlay()
        gtk.gdk.threads_leave()


  def SKLoginLogout(self, name, oldAddress, newAddress):
    self.cleanRef()
    self.connect()

  def SKSetMood(self,mood_msg):
    self.cleanRef()
    self.connect()
    retry = 3
    while (retry != 0):
      retry = retry - 1
      try:
        if self.connected and self.protSupported :
          self.skype_api.Invoke('%s %s' % (SKYPE_CMD_DICT.get('SetMood'),str(mood_msg)))
          break
      except:
        self.cleanRef()
        self.connect()


  def SKGetMood(self):
    self.cleanRef()
    self.connect()
    retry = 3
    mood_msg = None
    while (retry != 0):
      retry = retry - 1
      try:
        if self.connected and self.protSupported :
          mood_msg = self.skype_api.Invoke('%s' % SKYPE_CMD_DICT.get('GetMood'))
          if mood_msg.startswith('GET PROFILE RICH_MOOD_TEXT') :
            tmp = mood_msg[27:]
            mood_msg = str(tmp)
          elif mood_msg.startswith('PROFILE RICH_MOOD_TEXT') :
            tmp = mood_msg[23:]
            mood_msg = str(tmp)

        break
      except:
        self.cleanRef()
        self.connect()
    return mood_msg


  def isSkypeRunning(self):
    try:
      self.bus.get_object(SKYPE_API_NAME,SKYPE_API_PATH)
      return True
    except dbus.DBusException:
      return False


  def unhook(self):
    self.cleanRef()
    self.RBPause = None
    self.RBPlay = None
    self.RBIsPlaying = None
    if self.bus : self.bus = None
    if self.skype_stat: 
      self.skype_stat.remove()
      self.skype_stat = None
    self.pauseMessage = None
    self.oldSongTitle = None


