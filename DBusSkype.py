#    Rhythmbox Skype Mood Notifier - updates skype mood text from playlist
#    Copyright (C) 2007-2010 Christopher Gabijan
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

import gtk , gobject , time
import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop


SKYPE_API_NAME = 'com.Skype.API'
SKYPE_API_PATH = '/com/Skype'
SKYPE_CLIENT_PATH = '/com/Skype/Client'
PLUGIN_NAME = 'Rhythmbox-Mood-Notifier'


SKYPE_CMD_DICT = {
  'Connect' : 'Name',
  'Prot5':'PROTOCOL 5',
  'Prot7':'PROTOCOL 7',
  'SetMood':'SET PROFILE RICH_MOOD_TEXT',
  'GetMood':'GET PROFILE RICH_MOOD_TEXT',
  'CurrentUser' : 'GET CURRENTUSERHANDLE' 
}

SKYPE_CALL_BEGIN = ["EARLYMEDIA","RINGING","ROUTING","INPROGRESS"]
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
  def __init__(self, plungerUp = None, plungerDown = None):
    DBusGMainLoop(set_as_default=True)
    self.oldSkypeAddr = None
    self.curSkypeAddr = None
    self.isSkypeOn = False
    self.isStillOnCall = False
    self.connected = False
    self.skypeEventListener = None
    self.calls = {}
    self.users = {}
    #setup plunger (act as on the phone)
    if None is plungerUp :
      self.plungerUp   = self.plungerUpDef
    else :
      self.plungerUp   = plungerUp
    #setup plunger (act as putting down the phone)
    if None is plungerDown :
      self.plungerDown = self.plungerDownDef
    else :
      self.plungerDown = plungerDownDef
    #--initialize stuff --
    self.sk_hooking()




  #routine for registering skype-dbus
  def sk_hooking(self):
    self.bus = dbus.SessionBus()
    self.skype_stat = self.bus.add_signal_receiver(
             self.sk_onSkypeOnOff,
             'NameOwnerChanged',
             'org.freedesktop.DBus',
             'org.freedesktop.DBus',
             '/org/freedesktop/DBus',
             arg0=SKYPE_API_NAME)

    if self.isSkypeRunning() :
      self.isSkypeOn = True


  #routine for unregistering skype-dbus
  def sk_unHooking(self):
    if self.skype_stat: 
      self.skype_stat.remove()
      self.skype_stat = None
    if self.bus : self.bus = None
    


  #just add this for future -- LogIn / LogOut
  def sk_bindCBResp(self):
    self.skypeEventListener = ExpObjSkypeListener(self.bus,self.sk_onAnySkypeEvent)


  def sk_unBindCBResp(self):
    if self.skypeEventListener is not None : 
      self.skypeEventListener.deAttach()
      self.skypeEventListener = None


  #routine for connecting skype
  #depends on hooking
  def sk_connecting(self):
    try :
      ans = self.sk_invokeCmd('%s %s' % (SKYPE_CMD_DICT.get('Connect'),PLUGIN_NAME))
      if (ans == 'OK'): self.connected = True
      ans = self.sk_invokeCmd('%s' % SKYPE_CMD_DICT.get('Prot7'))
      if (ans == SKYPE_CMD_DICT.get('Prot7')): self.protSupported = True
      self.sk_bindCBResp()
    except:
      pass
    

  #routine for disconnecting skype
  #depends on connecting
  def sk_disconnecting(self):
    self.sk_unBindCBResp()
    self.protSupported = False
    self.connected = False


  #routine for throwing up commands
  def sk_invokeCmd(self, cmd):
    skypeAPI = self.bus.get_object(SKYPE_API_NAME,SKYPE_API_PATH)
    cmdResult = skypeAPI.Invoke(cmd)
    return cmdResult

  def sk_onAnySkypeEvent(self, cmdStr):
    if cmdStr.startswith('CALL'):
      cmdStrArr = cmdStr.split()
      if (len(cmdStrArr) == 4 and cmdStrArr[2] == 'STATUS'):
        self.qdCall(cmdStrArr[1],cmdStrArr[3])

    

  def sk_onSkypeOnOff(self, name, oldAddress, newAddress):
    self.oldSkypeAddr = oldAddress
    self.curSkypeAddr = newAddress

    #transition-event when a call was made but skype client was closed
    #we force clear the queue of the calls
    if ( self.isSkypeOn and self.isStillOnCall and not self.isSkypeRunning() ) :
      self.qdCall(None,None,True)

    #add here transition-event skype crashes

    #we can switch and notify events
    if self.isSkypeRunning() :
      # is On
      self.isSkypeOn = True
      self.sk_disconnecting()
      self.reconnect()
    else :
      self.isSkypeOn = False
      self.sk_disconnecting()



  #creates or sets the old message
  def saveOldMood(self):
    if self.isSkypeOn :
      currentUserHandle = self.sk_invokeCmd('%s' % SKYPE_CMD_DICT.get('CurrentUser'))
      if currentUserHandle.startswith('%s' % SKYPE_CMD_DICT.get('CurrentUser')[4:]) :
        if currentUserHandle[18:] not in self.users :
          mood_msg = self.sk_invokeCmd('%s' % SKYPE_CMD_DICT.get('GetMood'))
          tmp_mood = None
          if mood_msg.startswith('%s' % SKYPE_CMD_DICT.get('GetMood')[4:]) :
            tmp_mood = mood_msg[23:]
          if tmp_mood is None :
            self.users[currentUserHandle[18:]] =  ''
          else :
            self.users[currentUserHandle[18:]] =  str(tmp_mood)


  def getOldMood(self) :
    message = None
    if self.isSkypeOn :
      currentUserHandle = self.sk_invokeCmd('%s' % SKYPE_CMD_DICT.get('CurrentUser'))
      if currentUserHandle[18:] in self.users :
        message = self.users[currentUserHandle[18:]]

    return message


  def qdCall(self, callId, callStatus, forceClean = False):
    gtk.gdk.threads_enter()
    if forceClean : 
      self.calls.clear()
    
    else :
      # if id is existing
      if callId in self.calls :
        # and id is ending
        if callStatus in SKYPE_CALL_END :
          del self.calls[callId]
      #not existing
      else :
        if callStatus in SKYPE_CALL_BEGIN :
          self.calls[callId] = callStatus      

    #finally we notify
    if len(self.calls) > 0 :
      if not self.isStillOnCall :
        self.isStillOnCall = True
        self.plungerUp()
    elif len(self.calls) == 0 :
      if self.isStillOnCall :
        self.isStillOnCall = False
        self.plungerDown()

    gtk.gdk.threads_leave()


  def plungerUpDef(self):
    print "plunger up"

  def plungerDownDef(self):
    print "plunger down"

  def reconnect(self):
    # determine if skype is on
    if self.isSkypeOn :
      if not self.connected :
        self.sk_connecting()
      #try 3 times until die
      for i in range (0 , 3 ):
        if self.isUserLoggedIn() : 
          break
        else :
          self.sk_disconnecting()
          if (i!=2) :
            self.sk_connecting()
    

  def setMood(self, moodmessage):
    self.reconnect()
    if self.isSkypeOn :
      if self.isUserLoggedIn() :
        self.saveOldMood()
        self.sk_invokeCmd('%s %s' % (SKYPE_CMD_DICT.get('SetMood'), str(moodmessage)))

  def getMood(self):
    mood_msg  = None
    self.reconnect()
    if self.isSkypeOn :
      if self.isUserLoggedIn() :
        self.saveOldMood()
        mood_msg = self.sk_invokeCmd('%s' % (SKYPE_CMD_DICT.get('GetMood')))
        if mood_msg.startswith('GET PROFILE RICH_MOOD_TEXT') :
          tmp = mood_msg[27:]
          mood_msg = str(tmp)
        elif mood_msg.startswith('PROFILE RICH_MOOD_TEXT') :
          tmp = mood_msg[23:]
          mood_msg = str(tmp)
    return mood_msg



  def isUserLoggedIn(self):
    # check if skype is on and connected
    if ( self.isSkypeOn and self.connected and self.protSupported ) :
      currentUserHandle = self.sk_invokeCmd('%s' % SKYPE_CMD_DICT.get('CurrentUser'))
      if currentUserHandle.startswith('%s' % SKYPE_CMD_DICT.get('CurrentUser')[4:]) :
        return True
      else :
        return False
    return False



  def isSkypeRunning(self):
    try:
      self.bus.get_object(SKYPE_API_NAME,SKYPE_API_PATH)
      return True
    except dbus.DBusException:
      return False




