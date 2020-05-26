from riotwatcher import LolWatcher, ApiError
from api_key import key
import pandas as pd
import time

watcher = LolWatcher(key)
region_na = 'na1'
version = '10.10.3216176'

# Shit function to enforce rate limit
def api_call(func, *args):
    time.sleep(2)
    try:
        return func(*args)
    except Exception:
        print("Oops")
        return api_call(func, *args)

# account_id from username+region
def get_account_id(name, region):
    return api_call(watcher.summoner.by_name, region, name)['accountId']

# Note: QueueID for aram is 450
# Returns list of game_ids corresponding to aram games played by this player
def get_aram_games_n(account_id, region, begin, end):
    return [entry['gameId'] for entry in watcher.match.matchlist_by_account(region, account_id, queue=['450'], begin_index=begin, end_index=end)['matches']]
def get_aram_games(account_id, region, begin, end):
    return api_call(get_aram_games_n, account_id, region, begin, end)

# Returns dict of {champion_key: champion_name}
def get_champ_dict():
    champ_dict = {}
    for champ_name, champ_entry in api_call(watcher.data_dragon.champions, version)['data'].items():
        champ_dict[champ_entry['key']] = champ_name
    return champ_dict

# Returns match from game_id
def get_match(game_id, region):
    return api_call(watcher.match.by_id, region, game_id)

# Returns (win: bool, champ_name: string) for whether player won or not
def get_match_info(match, username, champ_dict):
    # Get participant id from username
    participantId = None
    for participant in match['participantIdentities']:
        if participant['player']['summonerName'] == username:
            participantId = participant['participantId']
    # Get champ + win status from participant id
    for participant in match['participants']:
        if participant['participantId'] == participantId:
            return (participant['stats']['win'], champ_dict[str(participant['championId'])])

# Returns list of (win: bool, champ_name: string) for a given player
def get_aram_history(username, region, game_count, champ_dict):
    aram_history, aram_games = [], []
    account_id = get_account_id(username, region)
    for start in range(0, game_count, 10):
        aram_games.extend(get_aram_games(account_id, region, start, start+10))
    for game in aram_games:
        match = get_match(game, region)
        match_info = get_match_info(match, username, champ_dict)
        aram_history.append(match_info)
    return aram_history

# Returns dict of {champion: (win_count, games_played)} given aram history
def aggregate_aram_history(aram_history, champ_dict):
    champ_wl = {}
    for champ in champ_dict.values():
        champ_wl[champ] = (0, 0)
    for win, champ in aram_history:
        champ_wl[champ] = (champ_wl[champ][0] + win, champ_wl[champ][1] + 1)
    return champ_wl

# Output aggregated history to csv file w/ winrate
def output_history(aggregated_history, username):
    rows = [[champ, str(entry[0]), str(entry[1]), str(entry[0]/max(1, entry[1]))] for champ, entry in aggregated_history.items()]
    field_names = ['champion', 'wins', 'games played', 'winrate']
    df = pd.DataFrame(rows, columns=field_names)
    df.sort_values(by=['games played'], inplace=True, ascending=False)
    df.to_csv(username + '.csv', index=False)

# Outputs csv file with winrates from given player for last n games
def process_player(username, game_count):
    print('ETA: ~%d minutes' % (game_count/20))
    champ_dict = get_champ_dict()
    aram_history = get_aram_history(username, region_na, game_count, champ_dict)
    aggregated_history = aggregate_aram_history(aram_history, champ_dict)
    output_history(aggregated_history, username)

process_player('crushsquid', 1000)