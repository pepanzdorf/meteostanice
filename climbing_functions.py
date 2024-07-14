def create_climbing_stats_user(df):
    grouped_by_boulder = df.sort_values('sent_date').groupby('boulder_id')
    challenges = df.drop_duplicates(subset=['boulder_id', 'challenge_id'])
    grouped_by_grade = grouped_by_boulder.first().groupby('grade')
    stats = {
        "all_sends": len(df),
        "challenges": sum(challenges['challenge_id'] != 1),
    }
    sum_sends = 0
    sum_flashes = 0
    unique_sends = {}
    for grade, group in grouped_by_grade:
        sends_grade = len(group)
        flashes = len(group[group['attempts'] == 0])
        sum_sends += sends_grade
        sum_flashes += flashes
        unique_sends[grade] = {'sends': sends_grade, 'flashes': flashes}

    stats['unique_sends'] = unique_sends
    stats['sum_sends'] = sum_sends
    stats['sum_flashes'] = sum_flashes

    unduplicated = df.drop_duplicates(subset=['boulder_id', 'challenge_id'])
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

    stats['score'] = score

    return stats


def create_climbing_stats(df):
    grouped_by_user = df.sort_values('sent_date').groupby('username')
    stats = {}
    for username, group in grouped_by_user:
        stats[username] = create_climbing_stats_user(group)

    # sort by score
    stats = {k: v for k, v in sorted(stats.items(), key=lambda item: item[1]['score'], reverse=True)}
    # as array
    stats = [(k, v) for k, v in stats.items()]

    return stats
