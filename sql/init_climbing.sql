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
    icon_url TEXT,
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

CREATE VIEW climbing.boulder_grades AS
SELECT
    b.id,
    COALESCE(AVG(s.grade), -1) as average_grade,
    COALESCE(AVG(s.rating), -1) as average_rating,
    s.angle
FROM
    climbing.boulders b
LEFT JOIN
    climbing.sends s ON b.id = s.boulder_id
GROUP BY
    b.id, b.name, b.description, b.build_time, s.angle;


CREATE VIEW climbing.hold_counts AS
SELECT
    h.id,
    COUNT(bh.boulder_id) AS count
FROM
    climbing.holds h
LEFT JOIN
    climbing.boulder_holds bh ON h.id = bh.hold_id
GROUP BY
    h.id
