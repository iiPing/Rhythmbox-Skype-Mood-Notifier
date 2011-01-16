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
import rhythmdb, rb
from DBusSkype import SkypeRhythmboxMediator

STRM_SONG_ARTIST = 'rb:stream-song-artist'
STRM_SONG_TITLE  = 'rb:stream-song-title'




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
    print "getting old mood message %s" % self.old_mood_msg
    self.psc_id = self.player.connect('playing-song-changed', self.song_changed)
    self.pspc_id = self.player.connect('playing-song-property-changed', self.song_property_changed)


  def deactivate(self,shell):
    if(self.old_mood_msg):
      print "setting back old mood message %s" % self.old_mood_msg
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

  def playerPlay(self):
    player= self.shell.get_player()
    if(player): player.play()

  def playerPause(self):
    player= self.shell.get_player()
    if(player): player.pause()

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
    retval = '<SS type="music">(music)</SS> '
    if artist and artist != 'Unknown' : 
      retval += ' '+ artist
    if title :
      if artist and artist != 'Unknown' :
        retval += ' -'
      retval += ' '+title
    return retval

