import requests
import nba.constants as constants
import nba.game as game
import nba.scoreboard as scoreboard
from datetime import datetime
from datetime import date
from operator import itemgetter
import pandas as pd
from difflib import get_close_matches


class PlayerNotFoundException(Exception):
    pass


NBA_URL = "http://data.nba.net/data/10s/prod/v1/"
PROFILE_URL = "https://ak-static.cms.nba.com/wp-content/uploads/headshots/nba/"

"""
getPlayerID
"""


def getPlayerID(fname, lname=""):

    fname = fname.lower()
    lname = lname.lower()
    full_name = "{} {}".format(fname, lname)

    df_stats = constants.df_player_stats

    # Last name could be blank
    if lname == "":
        players = df_stats[(df_stats['firstName_comp'] == fname) | (df_stats['lastName_comp'] == fname)]
    else:
        players = df_stats[(df_stats['firstName_comp'] == fname) & (df_stats['lastName_comp'] == lname)]

    if len(players) > 0:
        return players.iloc[0].to_dict()

    # Exact name matching didnt work, try do match (check for possible typo)
    # Last name could be blank
    if lname == "":
        all_names = df_stats['firstName_comp'].tolist() + df_stats['lastName_comp'].tolist()
        matches = get_close_matches(fname, all_names)
        players = df_stats[(df_stats['firstName_comp'] == matches[0]) | (df_stats['lastName_comp'] == matches[0])]
    else:
        all_names = df_stats['fullName_comp'].tolist()
        matches = get_close_matches(full_name, all_names)
        players = df_stats[(df_stats['fullName_comp'] == matches[0])]

    if len(players) > 0:
        return players.iloc[0].to_dict()

    # Didnt find exact or matching, raise error
    raise PlayerNotFoundException

def getPlayerSummary(player):
    return "{} {}({}) ".format(
        player["firstName"], player["lastName"], constants.id_to_team_name[int(player["teamId"])]
    )


def getPlayerLast3(fName, lName):
    try:
        player = getPlayerID(fName, lName)
    except PlayerNotFoundException:
        return "Player name not found"

    player_id = player["personId"]
    url = "{}{}/players/{}_gamelog.json".format(NBA_URL, str(constants.SEASON_YEAR), str(player_id))
    response = requests.get(url)
    data = response.json()["league"]["standard"]
    ret = getPlayerSummary(player)

    for i in range(2, -1, -1):
        stats = data[i]["stats"]
        ret = "{}{} PTS/{} REBS/{} AST".format(ret, stats['points'], stats['totReb'], stats['assists'])
        if data[i]["isHomeGame"]:
            if data[i]["hTeam"]["isWinner"]:
                wl = "W"
            else:
                wl = "L"
            ret = '{}in {} vs {}; '.format(ret, wl, str(constants.id_to_team_name[int(data[i]["vTeam"]["teamId"])]))
        else:
            if data[i]["vTeam"]["isWinner"]:
                wl = "W"
            else:
                wl = "L"
            ret = ret + "in " + wl + " @ " + str(constants.id_to_team_name[int(data[i]["hTeam"]["teamId"])]) + "; "
    return ret


def getPlayerStats(fName,lName):
    try:
        player = getPlayerID(fName, lName)
    except PlayerNotFoundException:
        return "Player name not found"

    playerid = player["personId"]
    url = "{}{}/players/{}_profile.json".format(NBA_URL, str(constants.SEASON_YEAR),  str(playerid))
    response = requests.get(url)
    data1 = response.json()
    data = data1["league"]["standard"]["stats"]["latest"]

    # If were in the playoffs, return regular season stats
    if data["seasonStageId"] == 4:
        data = data1["league"]["standard"]["stats"]["regularSeason"]["season"][1]["total"]

    summary = getPlayerSummary(player)
    stats = scoreboard.getStats(data, constants.PLAYER_STATS, constants.PLAYER_STATS_ID)
    return summary + stats


def getPlayerLiveStats(fName, lName):
    try:
        player = getPlayerID(fName, lName)
    except PlayerNotFoundException:
        return "Player name not found"

    boxscore = game.getBoxScore(int(player["teamId"]))
    if str(boxscore['game']['homeTeam']['teamId']) == player['teamId']:
        team = boxscore['game']['homeTeam']
        is_home = True
    else:
        team = boxscore['game']['awayTeam']
        is_home = False
    for team_player in team['players']:
        if str(team_player["personId"]) in [player["PLAYER_ID"],  player["personId"]]:
            ret = getPlayerSummary(player)
            if is_home:
                ret += 'vs {} , '.format(constants.id_to_team_name[int(boxscore["game"]["awayTeam"]["teamId"])])
            else:
                ret += '@ {} , '.format(constants.id_to_team_name[int(boxscore["game"]["homeTeam"]["teamId"])])

            team_player['statistics']['minutes'] = team_player[
                'statistics'
            ]['minutesCalculated'].replace("PT", "").replace("M", "")
            live_stats = scoreboard.getStats(
                team_player['statistics'],
                constants.PLAYER_LIVESTATS,
                constants.PLAYER_LIVESTATS_ID
            )
            return ret + live_stats

    return getPlayerSummary(player) + " is inactive."


def get_remain(flag, stat):
    if flag is True:
        return stat
    elif stat >= 10:
        return 0
    else:
        return 10 - stat


def tripDubWatch(fName, lName):
    try:
        player = getPlayerID(fName, lName)
    except PlayerNotFoundException:
        return "Player name not found"

    boxscore = game.getBoxScore(int(player["teamId"]))
    active_players = boxscore["stats"]["activePlayers"]
    ret = ""
    tail = ""
    for stats in active_players:
        if stats["personId"] == player["personId"]:
            ret = getPlayerSummary(player)
            triple_double = [
                ("pts", int(stats["points"])),
                ("ast", int(stats["assists"])),
                ("blk", int(stats["blocks"])),
                ("stl", int(stats["steals"])),
                ("reb", int(stats["totReb"]))
            ]
            triple_double.sort(key=itemgetter(1),reverse=True)
            flag = False
            if triple_double[2][1] >= 10:
                ret += "HAS COMPLETED A TRIPLE DOUBLE: "
                flag = True
            elif boxscore["basicGameData"]["statusNum"] == constants.GAME_STATUS_FINAL:
                ret += "did not finish the game with a triple double: "
                flag = True
            else:
                ret += "still needs: "
                tail = " for a triple double"

            stat_strings = []
            for k in range(3):
                stat_pair = triple_double[k]
                if flag or stat_pair[1] < 10:
                    stat_strings.append(str(get_remain(flag, stat_pair[1])) + stat_pair[0])

            ret += ", ".join(stat_strings)
            ret += tail
            if boxscore["basicGameData"]["hTeam"]["teamId"] == player["teamId"]:
                ret += " (vs {})".format(constants.id_to_team_name[int(boxscore["basicGameData"]["vTeam"]["teamId"])])
            else:
                ret += " (@ {})".format(constants.id_to_team_name[int(boxscore["basicGameData"]["hTeam"]["teamId"])])

    if ret == "":
        ret = getPlayerSummary(player) + "is inactive."

    return ret


def calculate_age(birth):
    born = datetime.strptime(birth, '%Y-%m-%d').date()
    today = date.today()
    return str(today.year - born.year - ((today.month, today.day) < (born.month, born.day)))


def getProfile(fName, lName):
    try:
        player = getPlayerID(fName, lName)
    except PlayerNotFoundException:
        return "Player name not found"

    photo_url = "{}{}/{}/260x190/{}.png".format(
        PROFILE_URL, player["teamId"], constants.SEASON_YEAR, player["personId"]
    )

    profile = "{}#{}, {}, {}'{}{}, {}, age {}".format(
        getPlayerSummary(player),
        player['jersey'], player["pos"],
        player["heightFeet"], player["heightInches"], "''",
        player['weightPounds'], calculate_age(player["dateOfBirthUTC"])
    )
    return "{} {}".format(photo_url, profile)
