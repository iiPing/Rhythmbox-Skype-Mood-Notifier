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

import cgi
import gtk, gtk.glade
import ConfigParser
import rhythmdb, rb
from DBusSkype import SkypeRhythmboxMediator
from string import Template

STRM_SONG_ARTIST = 'rb:stream-song-artist'
STRM_SONG_TITLE  = 'rb:stream-song-title'
RSMN_CONFIG_FILENAME  = 'plugin.conf'

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

    self.dialog = None
    self.txFormat = None
    self.txPause = None
    self.config = ConfigParser.ConfigParser()
    self.loadConfig()
    self.skype.pauseMessage = self.config.get('skype','pausemessage')


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

    del self.dialog
    del self.txFormat
    del self.txPause
    del self.config

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

    artist = cgi.escape(artist)
    title = cgi.escape(title)

    stat = self.format_resp(artist,title)
    self.skype.SKSetMood(stat)
    return 1


  def format_resp(self,artist,title):
    self.loadConfig()
    retval = Template(self.config.get('skype','moodformat'))
    #retval = '<SS type="music">(music)</SS> '
    #if artist and artist != 'Unknown' : 
    #  retval += ' '+ artist
    #if title :
    #  if artist and artist != 'Unknown' :
    #    retval += ' -'
    #  retval += ' '+title
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
      
      self.loadConfig()

      self.txFormat.set_text(self.config.get('skype','moodformat'))
      self.txPause.set_text(self.config.get('skype','pausemessage'))

      return self.dialog

  def dumpConfigFile(self):
    configFile = open(RSMN_CONFIG_FILENAME,'wb')
    self.config.write(configFile)
    configFile.close()

  def loadConfig(self):
    if self.fileConfigExists() :
      self.config.read(RSMN_CONFIG_FILENAME)
    else :
      #create the config and save it
      self.config.add_section('skype')
      self.config.set('skype','moodformat','<SS type="music">(music)</SS> $TITLE - $ARTIST')
      self.config.set('skype','pausemessage','(music - paused)')
      self.dumpConfigFile()

  def saveConfigFromDialog(self,widget):
    self.config.set('skype','moodformat',self.txFormat.get_text())
    self.config.set('skype','pausemessage',self.txPause.get_text())
    self.dumpConfigFile()
    self.skype.pauseMessage = self.txPause.get_text()
    self.dialog.hide()

  def hideDialog(self,widget):
    self.dialog.hide()

  def fileConfigExists(self):
    try:
      file = open(RSMN_CONFIG_FILENAME)
    except IOError:
      exists = False
    else:
      exists = True
    return exists


