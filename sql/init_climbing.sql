CREATE SCHEMA climbing;
CREATE TABLE climbing.boulders (
    id SERIAL UNIQUE PRIMARY KEY,
    name TEXT,
    description TEXT,
    build_time timestamp,
    built_by int REFERENCES climbing.users(id)
);
CREATE TABLE climbing.holds (
    id SERIAL PRIMARY KEY,
    path TEXT,
    is_volume BOOLEAN DEFAULT false
);
CREATE TABLE climbing.boulder_holds (
    boulder_id int REFERENCES climbing.boulders(id) ON DELETE CASCADE,
    hold_id int REFERENCES climbing.holds(id),
    hold_type int,
    PRIMARY KEY (boulder_id, hold_id)
);
CREATE TABLE climbing.users (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    admin BOOLEAN DEFAULT FALSE,
    icon_url TEXT default '/static/default_icon.jpg',
    description TEXT,
    border int default 0
);
CREATE TABLE climbing.sends (
    id SERIAL UNIQUE PRIMARY KEY,
    user_id int REFERENCES climbing.users(id) ON DELETE CASCADE,
    boulder_id int REFERENCES climbing.boulders(id) ON DELETE CASCADE,
    grade int,
    angle int,
    sent_date timestamp,
    attempts int,
    rating int,
    challenge_id int REFERENCES climbing.challenges(id)
);
CREATE TABLE climbing.challenges (
    id SERIAL UNIQUE PRIMARY KEY,
    name TEXT,
    description TEXT,
    score float
);
CREATE TABLE climbing.favourites (
    user_id int REFERENCES climbing.users(id) ON DELETE CASCADE,
    boulder_id int REFERENCES climbing.boulders(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, boulder_id)
);
CREATE TABLE climbing.comments (
    id SERIAL UNIQUE PRIMARY KEY,
    user_id int REFERENCES climbing.users(id) ON DELETE CASCADE,
    boulder_id int REFERENCES climbing.boulders(id) ON DELETE CASCADE,
    date timestamp,
    text TEXT
);
CREATE TABLE climbing.tags (
    id SERIAL UNIQUE PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE climbing.boulder_tags (
    boulder_id int REFERENCES climbing.boulders(id) ON DELETE CASCADE,
    tag_id int REFERENCES climbing.tags(id),
    PRIMARY KEY (boulder_id, tag_id)
);
CREATE TABLE climbing.config (
    key TEXT PRIMARY KEY,
    value TEXT
);


CREATE VIEW climbing.boulder_grades AS
SELECT
    b.id,
    COALESCE(AVG(s.grade), -1) as average_grade,
    COALESCE(AVG(s.rating), -1) as average_rating,
    s.angle
FROM
    climbing.boulders b
LEFT JOIN
    (SELECT * FROM climbing.sends WHERE challenge_id = 1) s ON b.id = s.boulder_id
GROUP BY
    b.id, b.name, b.description, b.build_time, s.angle;


CREATE VIEW climbing.hold_counts AS
SELECT
    h.id,
    jsonb_object_agg(
        COALESCE(bh.hold_type, -1),
        COALESCE(count, 0)
    ) AS types_counts
FROM
    climbing.holds h
LEFT JOIN (
    SELECT
        hold_id,
        hold_type,
        COUNT(boulder_id) AS count
    FROM
        climbing.boulder_holds
    GROUP BY
        hold_id,
        hold_type
) bh ON h.id = bh.hold_id
GROUP BY
    h.id
ORDER BY
    h.id;

CREATE VIEW climbing.hold_boulders AS
SELECT
    h.id,
    array_agg(
        ARRAY[b.name, ROUND(bg.average_grade)::TEXT]
    ) as boulders
FROM
    climbing.holds h
LEFT JOIN
    climbing.boulder_holds bh on h.id = bh.hold_id
LEFT JOIN climbing.boulders b on bh.boulder_id = b.id
LEFT JOIN climbing.boulder_grades bg on b.id = bg.id
GROUP BY h.id;

CREATE VIEW climbing.tags_by_boulder AS
SELECT
    b.id as boulder_id,
    COALESCE(array_agg(t.id), '{}') as tags
FROM
    climbing.boulders b
LEFT JOIN climbing.boulder_tags bt ON b.id = bt.boulder_id
LEFT JOIN climbing.tags t ON bt.tag_id = t.id
GROUP BY
    b.id;