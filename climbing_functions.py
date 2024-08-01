import math


def create_climbing_stats_user(df, grade_counts):
    grouped_by_boulder = df.sort_values('sent_date').groupby('boulder_id')
    unduplicated = df.drop_duplicates(subset=['boulder_id', 'challenge_id'])
    grouped_by_grade = grouped_by_boulder.first().groupby('grade')
    stats = {
        "all_sends": len(df),
        "challenges": sum(unduplicated['challenge_id'] != 1),
    }
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
        if i in completed_grades and i+1 in completed_grades and i+2 in completed_grades:
            if (grade_counts[i] + grade_counts[i+1] + grade_counts[i+2]) != 0:
                completed_grades_joint.append(i//3)
        if i == 51 and i in completed_grades and i+1 in completed_grades:
            if (grade_counts[i] + grade_counts[i + 1]) != 0:
                completed_grades_joint.append(i // 3)

    stats['unique_sends'] = unique_sends
    stats['sum_sends'] = sum_sends
    stats['sum_flashes'] = sum_flashes
    stats['completed_grades'] = completed_grades_joint
    stats['icon'] = df['icon_url'].values[0]
    stats['user_description'] = df['user_description'].values[0]

    grouped_by_boulder = unduplicated.sort_values('sent_date').groupby('boulder_id')

    score = 0

    for boulder_id, group in grouped_by_boulder:
        for i, row in group.iterrows():
            penalty = 0
            if 4 > row['attempts'] > 0:
                penalty = 1
            elif 9 > row['attempts'] >= 4:
                penalty = 2
            elif row['attempts'] >= 9:
                penalty = 4

            score += ((row['grade'] + 1) * 5 - penalty) * row['score']

    stats['score'] = math.floor(score)

    return stats


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
