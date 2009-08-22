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

import gtk, gtk.glade, gconf
import rhythmdb, rb
from DBusSkype import SkypeRhythmboxMediator
from string import Template

STRM_SONG_ARTIST = 'rb:stream-song-artist'
STRM_SONG_TITLE  = 'rb:stream-song-title'

CONF_KEY_MOOD  = '/apps/rhythmbox/plugins/rbskypemoodnotify/MoodFormat'
CONF_KEY_PAUSE = '/apps/rhythmbox/plugins/rbskypemoodnotify/PauseMessage'

CONF_VAL_DEFAULT_MOOD = '<SS type="music">d(^_^)b</SS> $TITLE - $ARTIST'
CONF_VAL_DEFAULT_PAUSE = '<SS type="talking">\(^_^)_</SS> ...'

class RhythmboxSkypeMoodNotifier(rb.Plugin):

  def __init__(self):
    rb.Plugin.__init__(self)


  def activate(self, shell):
    self.old_mood_msg = None
    self.shell = shell
    self.player = shell.get_player()
    self.skype = SkypeRhythmboxMediator(self.player.pause,self.player.play,self.isPlayerPlaying)
    self.skype.hook()
    self.old_mood_msg = self.skype.SKGetMood()
    self.psc_id = self.player.connect('playing-song-changed', self.song_changed)
    self.pspc_id = self.player.connect('playing-song-property-changed', self.song_property_changed)
    #gui
    self.dialog = None
    self.txFormat = None
    self.txPause = None
    #for configuration
    self.conf_client = gconf.client_get_default()
    self.mood_msg = None
    self.pause_msg = None
    self.loadConfig()

  def deactivate(self,shell):
    if(self.old_mood_msg):
      self.skype.SKSetMood(self.old_mood_msg)
      self.old_mood_msg = None

    if(self.skype): self.skype.unhook()
    if(self.player): self.player = None
    self.shell.get_player().disconnect (self.psc_id)
    self.shell.get_player().disconnect (self.pspc_id)
    del self.old_mood_msg
    del self.pspc_id
    del self.psc_id
    del self.shell
    del self.player
    del self.skype
    #gui
    del self.dialog
    del self.txFormat
    del self.txPause
    #for configuration
    del self.conf_client
    del self.mood_msg
    del self.pause_msg

  def isPlayerPlaying(self):
    player= self.shell.get_player()
    if(player):
      return player.props.playing

  def song_changed(self, player, entry):
   db = self.shell.get_property('db')
   self.gaat(db,entry)


  def song_property_changed(self, player, uri, prop, old_val, new_val):
   db = self.shell.get_property('db')
   entry = player.get_playing_entry()
   self.gaat(db,entry)


  def gaat(self,db, entry):
    if db is None :
      return None
    if entry is None:
      return None
    if (self.old_mood_msg == None) : self.old_mood_msg = self.skype.SKGetMood()
    stream_song_title = db.entry_request_extra_metadata(entry,STRM_SONG_TITLE)
    if (stream_song_title) :
      artist = db.entry_request_extra_metadata(entry,STRM_SONG_ARTIST)
      title = stream_song_title
    else:
      artist = db.entry_get(entry, rhythmdb.PROP_ARTIST)
      title = db.entry_get(entry, rhythmdb.PROP_TITLE)
    stat = self.format_resp(artist,title)
    self.skype.SKSetMood(stat)
    return 1


  def format_resp(self,artist,title):
    retval = Template(self.mood_msg)
    return retval.substitute(TITLE=title, ARTIST=artist)


  def create_configure_dialog(self, dialog=None):
    axdic = {
      'on_btnCancel_clicked' : self.hideDialog,
      'on_btnSave_clicked' : self.saveConfigFromDialog
    }
    if not dialog:
      glade_file = self.find_file("pref.dialog")
      gladexml = gtk.glade.XML(glade_file)
      gladexml.signal_autoconnect(axdic)
      self.dialog = gladexml.get_widget('dialog1')
      self.txFormat = gladexml.get_widget('txFormat')
      self.txPause = gladexml.get_widget('txPause')
      


      self.txFormat.set_text(self.mood_msg)
      self.txPause.set_text(self.pause_msg)

      return self.dialog


  def loadConfig(self):
    self.mood_msg = self.conf_client.get_string(CONF_KEY_MOOD)
    self.pause_msg = self.conf_client.get_string(CONF_KEY_PAUSE)

    if self.mood_msg is None:
      self.conf_client.add_dir(CONF_KEY_MOOD,gconf.CLIENT_PRELOAD_NONE)
      self.conf_client.set_string(CONF_KEY_MOOD,CONF_VAL_DEFAULT_MOOD)
      self.mood_msg = self.conf_client.get_string(CONF_KEY_MOOD)

    if self.pause_msg is None:
      self.conf_client.add_dir(CONF_KEY_PAUSE,gconf.CLIENT_PRELOAD_NONE)
      self.conf_client.set_string(CONF_KEY_PAUSE,CONF_VAL_DEFAULT_PAUSE)
      self.pause_msg = self.conf_client.get_string(CONF_KEY_PAUSE)

    self.skype.pauseMessage = self.pause_msg

    #load listeners
    self.conf_client.notify_add(CONF_KEY_MOOD,self.newMoodSetup)
    self.conf_client.notify_add(CONF_KEY_PAUSE,self.newPauseSetup)
    

  def newMoodSetup(self, client, *args, **kwargs):
    self.mood_msg = client.get_string(CONF_KEY_MOOD)

  def newPauseSetup(self, client, *args, **kwargs):
    self.pause_msg = client.get_string(CONF_KEY_PAUSE)
    self.skype.pauseMessage = self.pause_msg

  def saveConfigFromDialog(self,widget):
    self.conf_client.set_string(CONF_KEY_MOOD,self.txFormat.get_text())
    self.conf_client.set_string(CONF_KEY_PAUSE,self.txPause.get_text())
    self.dialog.hide()

  def hideDialog(self,widget):
    self.dialog.hide()


