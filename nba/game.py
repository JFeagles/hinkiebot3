import json
import datetime
import requests
import pytz
import nba.constants as constants
import calendar
import nba.scoreboard as scoreboard

GAMES_URL = 'http://data.nba.net/data/10s/prod/v1/'

"""
Returns game if team is playing rn
"""


def isTeamPlaying(teamID):
    date = datetime.datetime.now(constants.TIME_ZONE)
    if date.hour < constants.SCOREBOARD_UPDATE_HOUR:
        date = date - datetime.timedelta(days=1)
    date = date.strftime('%Y%m%d')
    url = '{}{}/scoreboard.json'.format(GAMES_URL, date)
    response = requests.get(url)
    games = response.json()["games"]
    for i in range(0, len(games)):
        if(((int(games[i]["vTeam"]["teamId"]) == teamID) or
            (int(games[i]["hTeam"]["teamId"]) == teamID)) and
                (games[i]["statusNum"] == constants.GAME_STATUS_STARTED)):
            return games[i]
    return None


"""
Returns the current gameID for that teamID
"""


def getGame(teamID):
    game = isTeamPlaying(teamID)
    if game is not None:
        return game
    else:
        #team not playing rn,need to get it from logs
        url = "{}{}/teams/{}/schedule.json".format(
            GAMES_URL, constants.SEASON_YEAR, constants.id_to_team_name[teamID].lower()
        )
        print(url)
        response = requests.get(url)
        data = response.json()
        lastgame = data["league"]["lastStandardGamePlayedIndex"]
        return data["league"]["standard"][lastgame]


"""
Returns the Score of the current game for that teamID
"""


def getGameScore(teamID):
    print("score method")
    try:
        game = getGame(teamID)
        print(game)
        ret = "{} {} @ {} {}".format(
            constants.id_to_team_name[int(game["vTeam"]["teamId"])], game["vTeam"]["score"],
            constants.id_to_team_name[int(game["hTeam"]["teamId"])], game["hTeam"]["score"]
        )
        if game["statusNum"] == constants.GAME_STATUS_FINAL:
            ret += str(', FINAL')
        elif game["period"]["isHalftime"] is True:
            ret += str(', HALF')
        else:
            ret = ret + ", " + game["clock"] + " "
            period = game["period"]["current"]
            if period <= 4:
                ret += str(period) + "Q"
            else:
                ret += "OT"
        if game["seasonStageId"] == 4:
            ret += " (" + game["playoffs"]["seriesSummaryText"]+")"
        return ret

    except Exception as e:
        print(str(e))


def getBoxScore(teamID):
    gm = getGame(teamID)
    url = '{}{}/{}_boxscore.json'.format(GAMES_URL, gm["startDateEastern"], gm["gameId"])
    print(url)
    response = requests.get(url)
    data = response.json()
    return data


def getTeamStats(teamID):
    print("team stats command")
    boxscore = getBoxScore(teamID)
    stats = boxscore["stats"]
    hTeamId = boxscore["basicGameData"]["hTeam"]["teamId"]
    vTeamId = boxscore["basicGameData"]["vTeam"]["teamId"]
    ret = constants.id_to_team_name[int(teamID)]
    if int(hTeamId) == teamID:
        ret += " vs " + constants.id_to_team_name[int(vTeamId)] + ", "
        stats = stats["hTeam"]["totals"]
    else:
        ret += " @ " + constants.id_to_team_name[int(hTeamId)] + ", "
        stats = stats["vTeam"]["totals"]

    return ret + scoreboard.getStats(stats, constants.TEAM_STATS, constants.TEAM_STATS_ID)


"""
Parse game date and time data and convert to EST timezone
"""


def getDatetime(datetime_):
    date = datetime_.split("T")[0]
    time = datetime_.split("T")[1].split(".")[0]
    datetime_ = str(date) + str(" ") + str(time)
    datetime_ = datetime.datetime.strptime(datetime_, '%Y-%m-%d %H:%M:%S')
    datetime_ = datetime_.replace(tzinfo=pytz.utc).astimezone(constants.TIME_ZONE)
    day = calendar.day_name[datetime_.weekday()]
    return str(day) + ", " + datetime.datetime.strptime(
        str(datetime_).rsplit('-', 1)[0], '%Y-%m-%d %H:%M:%S'
    ).strftime("%m/%d/%Y %I:%M %p")
    


"""
Loads team schedule from data.nba.net
"""


def loadSched(teamID):
    url = '{}{}/teams/{}/schedule.json'.format(
        GAMES_URL, constants.SEASON_YEAR, str(constants.id_to_team_name[teamID].lower())
    )
    response = requests.get(url)
    return response.json()


"""
Get time,date and opponnent of next game
"""


def getNextGame(teamID):
    data = loadSched(teamID)
    lastGame = data["league"]["lastStandardGamePlayedIndex"]

    if isTeamPlaying(teamID) != None:
        lastGame = lastGame + 1
    dateTime = getDatetime(data["league"]["standard"][lastGame+1]["startTimeUTC"]) + " ET"

    if (data["league"]["standard"][lastGame+1]["vTeam"]["teamId"] == str(teamID)):

        return "{} @ {} , {}".format(
            constants.id_to_team_name[teamID],
            constants.id_to_team_name[int(data["league"]["standard"][lastGame+1]["hTeam"]["teamId"])],
            dateTime
        )
    else:
        return "{} @ {}, {}".format(
            constants.id_to_team_name[int(data["league"]["standard"][lastGame + 1]["vTeam"]["teamId"])],
            constants.id_to_team_name[teamID],
            dateTime
        )



"""
Returns the results of teamID last 5 games
"""


def getLast5(teamID):
    data = loadSched(teamID)
    lastGame = data["league"]["lastStandardGamePlayedIndex"]
    ret = "Last 5 " + str(constants.id_to_team_name[teamID]) + " games: "

    for i in range(1, 6):
        index = lastGame-(5-i)
        vTeamId = data["league"]["standard"][index]["vTeam"]["teamId"]
        hTeamId = data["league"]["standard"][index]["hTeam"]["teamId"]
        vTeamScore = int(data["league"]["standard"][index]["vTeam"]["score"])
        hTeamScore = int(data["league"]["standard"][index]["hTeam"]["score"])
        if ( vTeamId == str(teamID)):
            #team is on the road
            ret = ret + "@ " + constants.id_to_team_name[int(hTeamId)]
            if (vTeamScore > hTeamScore):
                ret = ret + " W, " + str(vTeamScore) + " - " + str(hTeamScore) + "/ "
            else:
                ret = ret + " L, " + str(vTeamScore) + " - " + str(hTeamScore) + "/ "
        else:
            #team is at home
            ret = ret + "vs " + constants.id_to_team_name[int(data["league"]["standard"][index]["vTeam"]["teamId"])]
            if (vTeamScore < hTeamScore):
                ret = ret + " W, " + str(vTeamScore) + " - " + str(hTeamScore) + "/ "
            else:
                ret = ret + " L, " + str(vTeamScore) + " - " + str(hTeamScore) + "/ "

    return ret
