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

import rhythmdb, rb
from DBusSkype import DBusSkype

STRM_SONG_ARTIST = 'rb:stream-song-artist'
STRM_SONG_TITLE  = 'rb:stream-song-title'




class RhythmboxSkypeMoodNotifier(rb.Plugin):

  def __init__(self):
    rb.Plugin.__init__(self)

  def activate(self, shell):
    self.skype = DBusSkype()
    self.old_mood_msg = self.skype.getStatus()
    self.shell = shell
    player = shell.get_player()
    self.psc_id = player.connect('playing-song-changed', self.song_changed)
    self.pspc_id = player.connect('playing-song-property-changed', self.song_property_changed)


  def deactivate(self,shell):
    if(self.old_mood_msg):
      self.skype.setStatus(self.old_mood_msg)
    self.shell.get_player().disconnect (self.psc_id)
    self.shell.get_player().disconnect (self.pspc_id)
    del self.old_mood_msg
    del self.pspc_id
    del self.psc_id
    del self.shell
    del self.skype


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
    stat = self.format_resp(artist,title)
    self.skype.setStatus(stat)
    return 1

  def format_resp(self,artist,title):
    retval = '(music) '
    if artist and artist != 'Unknown' : 
      retval += ' '+ artist
    if title :
      if artist and artist != 'Unknown' :
        retval += ' -'
      retval += ' '+title


    return retval

