// This should be a direct clone of the score calculation code in climbing_functions.py
let penalty = 0;
if (2 > attempts && attempts > 0) {
    penalty = 2;
} else if (6 > attempts && attempts >= 2) {
    penalty = 3;
} else if (9 > attempts && attempts >= 6) {
    penalty = 4;
} else if (attempts >= 9) {
    penalty = 5;
}

let multiplier = 1;
if (16 > grade && grade > 6) {
    multiplier = 2;
} else if (25 > grade && grade >= 16) {
    multiplier = 3;
} else if (34 > grade && grade >= 25) {
    multiplier = 4;
} else if (43 > grade && grade >= 34) {
    multiplier = 5;
} else if (grade >= 43) {
    multiplier = 6;
}

return Math.max(Math.floor(((grade + 1) * multiplier * 3 - penalty) * score), 0);