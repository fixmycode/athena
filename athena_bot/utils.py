import pickle
import random
import petname
import pytz
import re

from datetime import datetime

def read_datafile(filename):
    with open(filename, 'rb') as f:
        try:
            return pickle.load(f)
        except EOFError as e:
            print(e)
            return {}

def write_datafile(filename, data):
    with open(filename, 'wb') as f:
        pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
        return True

def to_camel(snake:str):
    first, *rest = snake.split('-')
    return ''.join([first.lower(), *map(str.title, rest)])

def make_teams(member_names, capacity):
    count = len(member_names)
    random.shuffle(member_names)
    team_cap = min(count // 2, capacity)
    spectators_count = count % team_cap
    teams = []
    while count > spectators_count:
        team = [member_names.pop() for i in range(team_cap)]
        teams.append(team)
        count -= team_cap
    spectators = member_names
    return (teams, spectators)

def make_team_messages(member_names, capacity):
    teams, spectators = make_teams(member_names, capacity)
    cardinals = ['first', 'second', 'third', 'fourth', 'next']
    messages = []
    bullets = list('🔵🔴🟢🟠🟡🟣')
    for i, t in enumerate(teams):
        cardinal = min(i, len(cardinals) - 1)
        team_name = petname.Generate(separator=' ', letters=10)
        if re.search(r'(sh|s)$', team_name):
            team_name = team_name + 'es'
        else:
            team_name = team_name + 's'
        team_members = f'{bullets[i]} '+f'\n{bullets[i]} '.join(t) if len(t) > 1 else f'{bullets[i]} {t[0]}'
        messages.append(f'The {cardinals[cardinal]} team are  **The {team_name.title()}**:\n{team_members}\n')
    if spectators:
        spect_names = '👁 '+'\n👁 '.join(spectators) if len(spectators) > 1 else f'👁 {spectators[0]}\n'
        many_match = 'these matches' if len(teams) > 2 else 'this match'
        if len(spectators) > 1:
            messages.append(f'The honorable spectators for {many_match} are:\n{spect_names}\n')
        else:
            messages.append(f'The honorable spectator for {many_match} is:\n{spect_names}\n')
    return messages

def local_time(zone_name):
    zone = pytz.timezone(zone_name)
    return datetime.now(zone)
