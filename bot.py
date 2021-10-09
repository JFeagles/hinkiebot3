from lib import ch
from nba import nbacommands

nbaprefix = "&"
nhlprefix = "#"
altnbaprefix = "/"

class HinkieBot(ch.RoomManager):
    def onConnect(self, room):
        print("Connected to "+room.name)
    
    def onReconnect(self, room):
        print("Reconnected to "+room.name)

    def onDisconnect(self, room):
        print("Disconnected from "+room.name)
        self.joinRoom(room.name)

    def onMessage(self, room, user, message):
        try:
            msg = str(message.body.lstrip(" "))
            print(msg)
            if msg[0] == nbaprefix or msg[0] == altnbaprefix:
                msg = msg[1:]
                try:
                    command, args = msg.split(" ", 1)
                    print("command: " + command)
                    print("args: " + args)
                    ret = nbacommands.runCommand(command.lower(), args)
                except Exception as exp:
                    ret = nbacommands.runCommand(msg.lower(), None)

                if ret is not None:
                    room.message(str(ret))
        except Exception as e:
            print(str(e))
rooms = ["hinkiebottesterxd"]#,"acleenba","csnphilly","nbcsphilly","acmemed3"]
bot_name = "HinkieBot"
bot_pw = ""
HinkieBot.easy_start(rooms, bot_name, bot_pw)
