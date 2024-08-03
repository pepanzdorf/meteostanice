import math
from datetime import datetime


def note_season(date):
    year = date.year
    month = date.month

    if month <= 5:
        return f"{year} 1"
    else:
        return f"{year} 2"


def create_climbing_stats_user(df, grade_counts):
    df['season'] = df['sent_date'].apply(note_season)
    current_season = note_season(datetime.now())
    unduplicated = df.drop_duplicates(subset=['boulder_id', 'challenge_id'])
    stats = {
        "all_sends": len(df),
        "challenges": sum(unduplicated['challenge_id'] != 1),
        'icon': df['icon_url'].values[0],
        'user_description': df['user_description'].values[0],
        'border': int(df['border'].values[0])
    }

    current_season_sends = False
    grouped_by_season = df.sort_values('sent_date').groupby('season')
    stats['previous_seasons'] = {}
    for season, group in grouped_by_season:
        if season == current_season:
            season_stats = create_season_stats(group, grade_counts, True)
            for key, value in season_stats.items():
                stats[key] = value
            current_season_sends = True
        else:
            stats['previous_seasons'][season] = create_season_stats(group, grade_counts, False)

    if not current_season_sends:
        stats['unique_sends'] = {}
        stats['sum_sends'] = 0
        stats['sum_flashes'] = 0
        stats['completed_grades'] = []
        stats['score'] = 0

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
    grouped_by_user = df.sort_values('sent_date').groupby('username')
    stats = {}
    for username, group in grouped_by_user:
        stats[username] = create_climbing_stats_user(group, grade_counts)

    # sort by score
    stats = {k: v for k, v in sorted(stats.items(), key=lambda item: item[1]['score'], reverse=True)}
    # as array
    stats = [(k, v) for k, v in stats.items()]

    return stats
