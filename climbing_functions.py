import math
from datetime import datetime


def note_season(date):
    year = date.year
    month = date.month

    if month <= 5:
        return f"{year} 1"
    else:
        return f"{year} 2"


def create_climbing_stats_user(df, grade_counts, sessions_stats):
    current_season = note_season(datetime.now())
    unduplicated = df.drop_duplicates(subset=['boulder_id', 'challenge_id'])

    unique_sessions = df[['year', 'month', 'day', 'season']].drop_duplicates()

    grouped_by_season = unique_sessions.groupby('season')
    sessions_stats = {}
    overall_seasons = 0
    for season, group in grouped_by_season:
        if season == current_season:
            sessions_stats['current'] = len(group)
        else:
            sessions_stats['previous_seasons'][season] = len(group)
        overall_seasons += len(group)

    sessions_stats['overall'] = overall_seasons

    stats = {
        "all_sends": len(df),
        "challenges": sum(unduplicated['challenge_id'] != 1),
        'icon': df['icon_url'].values[0],
        'user_description': df['user_description'].values[0],
        'border': int(df['border'].values[0]),
        'sessions': sessions_stats,
    }

    overall_score = 0
    current_season_sends = False
    grouped_by_season = df.sort_values('sent_date').groupby('season')
    stats['previous_seasons'] = {}
    for season, group in grouped_by_season:
        if season == current_season:
            season_stats = create_season_stats(group, grade_counts, True)
            for key, value in season_stats.items():
                stats[key] = value
            current_season_sends = True
            overall_score += season_stats['score']
        else:
            stats['previous_seasons'][season] = create_season_stats(group, grade_counts, False)
            overall_score += stats['previous_seasons'][season]['score']

    if not current_season_sends:
        stats['unique_sends'] = {}
        stats['sum_sends'] = 0
        stats['sum_flashes'] = 0
        stats['completed_grades'] = []
        stats['score'] = 0

    stats['overall_score'] = overall_score
    stats['unlocked_borders'], stats['to_unlock'] = completed_border_challenges(df, overall_score)

    return stats


def create_season_stats(df, grade_counts, is_current_season):
    grouped_by_boulder = df.sort_values('sent_date').groupby('boulder_id')
    grouped_by_grade = grouped_by_boulder.first().groupby('grade')
    unduplicated = df.drop_duplicates(subset=['boulder_id', 'challenge_id'])
    sum_sends = 0
    sum_flashes = 0
    completed_grades = []
    unique_sends = {}
    for grade, group in grouped_by_grade:
        sends_grade = len(group)
        flashes = len(group[group['attempts'] == 0])
        sum_sends += sends_grade
        sum_flashes += flashes
        unique_sends[grade] = {'sends': sends_grade, 'flashes': flashes}
        if len(group) == grade_counts[grade]:
            completed_grades.append(grade)

    for i in range(0, 52):
        if grade_counts[i] == 0:
            completed_grades.append(i)

    completed_grades = sorted(completed_grades)
    completed_grades_joint = []
    for i in range(0, 52, 3):
        if i in completed_grades and i + 1 in completed_grades and i + 2 in completed_grades:
            if (grade_counts[i] + grade_counts[i + 1] + grade_counts[i + 2]) != 0:
                completed_grades_joint.append(i // 3)
        if i == 51 and i in completed_grades and i + 1 in completed_grades:
            if (grade_counts[i] + grade_counts[i + 1]) != 0:
                completed_grades_joint.append(i // 3)

    grouped_by_boulder = unduplicated.sort_values('sent_date').groupby('boulder_id')

    score = 0

    for boulder_id, group in grouped_by_boulder:
        for i, row in group.iterrows():
            penalty = 0
            if 2 > row['attempts'] > 0:
                penalty = 2
            elif 6 > row['attempts'] >= 2:
                penalty = 3
            elif 9 > row['attempts'] >= 6:
                penalty = 4
            elif row['attempts'] >= 9:
                penalty = 5

            multiplier = 1
            if 16 > row['grade'] > 6:
                multiplier = 2
            elif 25 > row['grade'] >= 16:
                multiplier = 3
            elif 34 > row['grade'] >= 25:
                multiplier = 4
            elif 43 > row['grade'] >= 34:
                multiplier = 5
            elif row['grade'] >= 43:
                multiplier = 6

            score += max(math.floor(((row['grade'] + 1) * multiplier * 3 - penalty) * row['score']), 0)

    if is_current_season:
        return {
            'unique_sends': unique_sends,
            'sum_sends': sum_sends,
            'sum_flashes': sum_flashes,
            'completed_grades': completed_grades_joint,
            'score': score
        }
    else:
        return {
            'unique_sends': unique_sends,
            'score': score
        }


def create_climbing_stats(df, grade_counts):
    df['year'] = df['sent_date'].dt.year
    df['month'] = df['sent_date'].dt.month
    df['day'] = df['sent_date'].dt.day
    df['season'] = df['sent_date'].apply(note_season)

    current_season = note_season(datetime.now())

    unique_sessions = df[['year', 'month', 'day', 'season']].drop_duplicates()

    grouped_by_season = unique_sessions.groupby('season')
    sessions_stats = {}
    overall_seasons = 0
    for season, group in grouped_by_season:
        if season == current_season:
            sessions_stats['current'] = len(group)
        else:
            sessions_stats['previous_seasons'][season] = len(group)
        overall_seasons += len(group)

    sessions_stats['overall'] = overall_seasons

    grouped_by_user = df.sort_values('sent_date').groupby('username')
    stats = {'sessions': sessions_stats}
    user_stats = {}
    for username, group in grouped_by_user:
        user_stats[username] = create_climbing_stats_user(group, grade_counts, sessions_stats)

    # sort by score
    user_stats = {k: v for k, v in sorted(user_stats.items(), key=lambda item: item[1]['score'], reverse=True)}
    # as array
    user_stats = [(k, v) for k, v in user_stats.items()]

    stats['users'] = user_stats

    return stats


def completed_border_challenges(user_df, overall_score):
    unique_boulder_ids = user_df['boulder_id'].unique()
    sends_in_december = sum(user_df['sent_date'].dt.month == 12)
    unlocked_borders = [0]  # No border
    to_unlock = {}
    if overall_score >= 1000:
        unlocked_borders.append(1)
    if overall_score >= 5000:
        unlocked_borders.append(2)
    if overall_score >= 10000:
        unlocked_borders.append(3)
    if overall_score >= 20000:
        unlocked_borders.append(4)
    if overall_score >= 35000:
        unlocked_borders.append(5)
    if overall_score >= 50000:
        unlocked_borders.append(6)
    if overall_score >= 75000:
        unlocked_borders.append(7)
    if overall_score >= 100000:
        unlocked_borders.append(8)
    if all(elem in unique_boulder_ids for elem in [33, 99, 86, 20, 35]):
        # dirt border
        unlocked_borders.append(9)
    else:
        to_unlock[9] = [elem for elem in [33, 99, 86, 20, 35] if elem not in unique_boulder_ids]
    if all(elem in unique_boulder_ids for elem in [21, 4, 15, 28, 14, 13, 22]):
        # animal border
        unlocked_borders.append(10)
    else:
        to_unlock[10] = [elem for elem in [21, 4, 15, 28, 14, 13, 22] if elem not in unique_boulder_ids]
    if any(user_df['attempts'].values >= 10):
        # mud border
        unlocked_borders.append(11)
    if all(elem in unique_boulder_ids for elem in [105, 113, 30, 69, 68, 103]):
        # stone border
        unlocked_borders.append(12)
    else:
        to_unlock[12] = [elem for elem in [105, 113, 30, 69, 68, 103] if elem not in unique_boulder_ids]
    if all(elem in unique_boulder_ids for elem in [61, 52, 57, 58, 25, 72, 70, 77]):
        # water border
        unlocked_borders.append(13)
    else:
        to_unlock[13] = [elem for elem in [61, 52, 57, 58, 25, 72, 70, 77] if elem not in unique_boulder_ids]
    if all(elem in unique_boulder_ids for elem in [128, 84, 122, 73, 135, 133]):
        # muscle border
        unlocked_borders.append(14)
    else:
        to_unlock[14] = [elem for elem in [128, 84, 122, 73, 135, 133] if elem not in unique_boulder_ids]
    if all(elem in unique_boulder_ids for elem in [47, 97, 87, 63, 37]):
        # bandage border
        unlocked_borders.append(15)
    else:
        to_unlock[15] = [elem for elem in [47, 97, 87, 63, 37] if elem not in unique_boulder_ids]
    if sends_in_december >= 10:
        # ice border
        unlocked_borders.append(16)
    if all(elem in unique_boulder_ids for elem in [100, 114, 42, 23]):
        # caveman border
        unlocked_borders.append(17)
    else:
        to_unlock[17] = [elem for elem in [100, 114, 42, 23] if elem not in unique_boulder_ids]
    if all(elem in unique_boulder_ids for elem in [91, 83, 30, 67, 71, 116, 98]):
        # nature border
        unlocked_borders.append(18)
    else:
        to_unlock[18] = [elem for elem in [91, 83, 30, 67, 71, 116, 98] if elem not in unique_boulder_ids]
    if user_df[(user_df['sent_date'].dt.month == 12) & (user_df['sent_date'].dt.day == 22)].shape[0] > 0:
        # christmas border
        unlocked_borders.append(19)

    return unlocked_borders, to_unlock
