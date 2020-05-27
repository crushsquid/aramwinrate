from riotwatcher import LolWatcher, ApiError
from api_key import key
from rate_limit import RateLimitRule, RateLimiter
import pandas as pd
import constants

watcher = LolWatcher(key)

rules = [RateLimitRule(20, 1), RateLimitRule(100, 120)]
limiter = RateLimiter(rules)

# account_id from username+region
def get_account_id(name, region):
    summoner_info = limiter.call(watcher.summoner.by_name, region, name)
    account_id = summoner_info['accountId']
    return account_id

# Returns list of game_ids corresponding to aram games played by this player
def get_aram_games_not_limited(account_id, region, begin, end):
    match_info = watcher.match.matchlist_by_account(region, account_id, queue=[constants.ARAM], begin_index=begin, end_index=end)
    match_list = match_info['matches']
    game_ids = [match['gameId'] for match in match_list]
    return game_ids
def get_aram_games(account_id, region, begin, end):
    return limiter.call(get_aram_games_not_limited, account_id, region, begin, end)

# Returns dict of {champion_key: champion_name}
def get_champ_dict(region):
    versions = limiter.call(watcher.data_dragon.versions_for_region, region)
    version = versions['n']['champion']
    champion_info = limiter.call(watcher.data_dragon.champions, version)
    champion_names = champion_info['data']
    champ_dict = {champ_entry['key']: champ_name for champ_name, champ_entry in champion_names.items()}
    return champ_dict

# Returns match from game_id
def get_match(game_id, region):
    return limiter.call(watcher.match.by_id, region, game_id)

# Returns (win: bool, champ_name: string) for whether player won or not
def get_match_info(match, account_id, champ_dict):
    # Get participant id from username
    participant_identities = match['participantIdentities']
    participant_id = next(participant['participantId'] for participant in participant_identities if participant['player']['accountId'] == account_id)
    # Get champ + win status from participant id
    participants_info = match['participants']
    participant_info = None
    for participant in participants_info:
        if participant['participantId'] == participant_id:
            participant_info = participant
    participant_info = next(participant for participant in participants_info if participant['participantId'] == participant_id)

    win = participant_info['stats']['win']
    champ_id = participant_info['championId']
    champ = champ_dict[str(champ_id)]
    return (win, champ)

# Returns list of (win: bool, champ_name: string) for a given player
def get_aram_history(account_id, region, game_count, champ_dict, batch_size=10):
    aram_history, aram_games = [], []
    for start in range(0, game_count, batch_size):
        aram_games_batch = get_aram_games(account_id, region, start, start + batch_size)
        aram_games.extend(aram_games_batch)
    for game in aram_games:
        match = get_match(game, region)
        match_info = get_match_info(match, account_id, champ_dict)
        aram_history.append(match_info)
    return aram_history

# Returns dict of {champion: (win_count, games_played)} given aram history
def aggregate_aram_history(aram_history, champ_dict):
    champ_wl = {champ: (0, 0) for champ in champ_dict.values()}
    for win, champ in aram_history:
        win_count = champ_wl[champ][0] + win
        games_played = champ_wl[champ][1] + 1
        champ_wl[champ] = (win_count, games_played)
    return champ_wl

# Output aggregated history to csv file w/ winrate
def output_history(aggregated_history, username):
    rows = []
    for champ, entry in aggregated_history.items():
        win_count, games_played = entry
        winrate = win_count / max(1, games_played)
        row = [champ, win_count, games_played, winrate]
        rows.append(row)
    field_names = ['champion', 'wins', 'games played', 'winrate']
    df = pd.DataFrame(rows, columns=field_names)
    df.sort_values(by=['games played'], inplace=True, ascending=False)
    df.to_csv('data/' + username + '.csv', index=False)

# Outputs csv file with winrates from given player for last n games
def process_player(username, game_count):
    print('ETA: ~%d minutes' % (game_count/20))
    champ_dict = get_champ_dict(constants.REGION_NA)
    account_id = get_account_id(username, constants.REGION_NA)
    aram_history = get_aram_history(account_id, constants.REGION_NA, game_count, champ_dict)
    aggregated_history = aggregate_aram_history(aram_history, champ_dict)
    output_history(aggregated_history, username)

process_player('Dorito Sensei', 50)
