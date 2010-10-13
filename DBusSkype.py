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
  def __init__(self, ringHigh = None, ringLow = None):
    DBusGMainLoop(set_as_default=True)



    self.skypeEventListener = None
    self.calls = {}
    self.users = {}

    #ala filedescriptor for skype in dbus
    self.skype_fd  = None

    self.skype_protocolSupported = False

    #states --------------------------------------------
    
    # hooked is a state used for skype-dbus
    self.hooked = False

    # used to determine if skype is on or off
    self.skype_on = False

    # used to determine for "established connection"
    # established connection means if 2 commands has
    # been replied gracefully 
    # command 1
    # input  : Name Rhythmbox-Mood-Notifier
    # output : OK
    # command 2
    # input  : PROTOCOL 7
    # output : PROTOCOL 7
    self.skype_connected = False

    # a pseudo state used to determine if 
    # there is an actual call or
    # just on ringing state 
    self.skype_oncall = False


    #setup plunger (act as on the phone)
    if None is ringHigh :
      self.ringHigh   = self.ringHighDef
    else :
      self.plungerUp   = plungerUp
    #setup plunger (act as putting down the phone)
    if None is ringLow :
      self.ringLow = self.ringLowDef
    else :
      self.ringLow = ringLowDef




  #routine for registering skype-dbus
  def sk_hooking(self):
    try :
      if not self.hooked :
        self.bus = dbus.SessionBus()
        self.skype_fd = self.bus.add_signal_receiver(
                 self.sk_onSkypeOnOff,
                 'NameOwnerChanged',
                 'org.freedesktop.DBus',
                 'org.freedesktop.DBus',
                 '/org/freedesktop/DBus',
                 arg0=SKYPE_API_NAME)
        self.hooked = True
        self.skype_on = self.isSkypeRunning()
    except :
      pass




  #routine for unregistering skype-dbus
  def sk_unHooking(self):
    if self.hooked :
      self.skype_on = False
      if self.skype_fd: 
        self.skype_fd.remove()
        self.skype_fd = None
      if self.bus : self.bus = None
      self.hooked = False


  #skype-event-callback registration

  #only called during connecting
  def sk_bindCBResp(self):
    if self.skypeEventListener is None :
      self.skypeEventListener = ExpObjSkypeListener(self.bus,self.sk_onAnySkypeEvent)

  #only called during disconnecting
  def sk_unBindCBResp(self):
    if self.skypeEventListener is not None : 
      self.skypeEventListener.deAttach()
      self.skypeEventListener = None


  #routine for connecting skype
  #depends on hooking
  def sk_connecting(self):
    if self.hooked and self.skype_on :
      try :
        ans = self.sk_invokeCmd('%s %s' % (SKYPE_CMD_DICT.get('Connect'),PLUGIN_NAME))
        if (ans == 'OK'): self.skype_connected = True
        ans = self.sk_invokeCmd('%s' % SKYPE_CMD_DICT.get('Prot7'))
        if (ans == SKYPE_CMD_DICT.get('Prot7')): self.skype_protocolSupported = True
        self.sk_bindCBResp()
      except:
        pass
    

  #routine for disconnecting skype
  #depends on connecting
  def sk_disconnecting(self):
    self.sk_unBindCBResp()
    self.skype_protocolSupported = False
    self.skype_connected = False


  #routine for throwing up commands
  def sk_invokeCmd(self, cmd):
    ret_val = None
    if self.hooked and self.isSkypeRunning() :
      skypeAPI = self.bus.get_object(SKYPE_API_NAME,SKYPE_API_PATH)
      ret_val = skypeAPI.Invoke(cmd)
    return ret_val
    


  #this is the event-transition that will 
  #fire-up from skype
  #depends on sk_connecting()
  def sk_onAnySkypeEvent(self, cmdStr):
    if cmdStr.startswith('CALL'):
      cmdStrArr = cmdStr.split()
      if (len(cmdStrArr) == 4 and cmdStrArr[2] == 'STATUS'):
        self.qdCall(cmdStrArr[1],cmdStrArr[3])

  def sk_established(self):
    return (self.isSkypeRunning() and self.skype_connected and self.skype_protocolSupported)


  def sk_onSkypeOnOff(self, name, oldAddress, newAddress):

    #transition-event when a call was made but skype client was closed
    #we force clear the queue of the calls
    if ( self.skype_on and self.skype_oncall and not self.isSkypeRunning() ) :
      self.qdCall(None,None,True)

    #add here transition-event like: skype crashes and whatnot

    #we can switch and notify events
    if self.isSkypeRunning() :
      # is On
      self.skype_on = True
      self.reconnect(False)
    else :
      self.skype_on = False
      self.sk_disconnecting()

  def reconnect(self, normalCall = True):
    # determine if skype is on
    if normalCall :
      if not self.sk_established() :
        self.sk_connecting()

    #try 3 more times before we give up
    if self.skype_on :
      for i in range (0 , 3 ):
        if self.isAuthorized() : 
          break
        else :
          self.sk_disconnecting()
          if (i!=2) : self.sk_connecting()


  # QueueD Call
  # a routine that has a function of a call queue 
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
      if not self.skype_oncall :
        self.skype_oncall = True
        self.plungerUp()
    elif len(self.calls) == 0 :
      if self.skype_oncall :
        self.skype_oncall = False
        self.plungerDown()
    gtk.gdk.threads_leave()


  def isAuthorized(self):
    # check if skype is on and connected
    ret_val = False
    if self.sk_established() :
      currentUserHandle = self.sk_invokeCmd('%s' % SKYPE_CMD_DICT.get('CurrentUser'))
      if currentUserHandle.startswith('%s' % SKYPE_CMD_DICT.get('CurrentUser')[4:]) :
        ret_val =  True
    return ret_val



  #creates or sets the old message
  def saveOldMood(self,requireReconnect=True):
    if requireReconnect :
      self.reconnect()

    if self.isAuthorized() :
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


  def getOldMood(self , requireReconnect=True) :
    if requireReconnect :
      self.reconnect()

    message = None
    if self.isAuthorized() :
      currentUserHandle = self.sk_invokeCmd('%s' % SKYPE_CMD_DICT.get('CurrentUser'))
      if currentUserHandle[18:] in self.users :
        message = self.users[currentUserHandle[18:]]
    return message



  
  # default functions modelled from the old 
  # telephone where a ringing signal was invoked
  def ringHighDef(self):
    print "volt high toggled ringing"

  # where a ringing signal was revoked
  def ringLowDef(self):
    print "volt low toggled no ringing"


  def fSetMood(self,moodmessage):
    # transition event when a playlist was forced to play while there 
    # was an ongoing call
    self.qdCall(None,None,True)
    self.setMood(moodmessage)

  

  def setMood(self, moodmessage):
    # Moved to fSetMood()
    # transition event when a playlist was forced to play while there 
    # was an ongoing call
    #if ( self.skype_oncall and self.isAuthorized() ) :
    #  self.qdCall(None,None,True)

    if not self.isAuthorized() :
      self.reconnect()

    self.saveOldMood(False)
    self.sk_invokeCmd('%s %s' % (SKYPE_CMD_DICT.get('SetMood'), str(moodmessage)))

  def getMood(self):
    mood_msg  = None

    if not self.isAuthorized() :
      self.reconnect()

    self.saveOldMood(False)
    mood_msg = self.sk_invokeCmd('%s' % (SKYPE_CMD_DICT.get('GetMood')))
    if mood_msg.startswith('GET PROFILE RICH_MOOD_TEXT') :
      tmp = mood_msg[27:]
      mood_msg = str(tmp)
    elif mood_msg.startswith('PROFILE RICH_MOOD_TEXT') :
      tmp = mood_msg[23:]
      mood_msg = str(tmp)
    return mood_msg


  def isSkypeRunning(self):
    ret_val = False
    if self.hooked :
      try:
        self.bus.get_object(SKYPE_API_NAME,SKYPE_API_PATH)
        ret_val = True
      except dbus.DBusException:
        pass
    return ret_val





