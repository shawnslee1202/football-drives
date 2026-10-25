-- Raw CFBD response tables; full bodies remain private.
CREATE TABLE drives(id TEXT PRIMARY KEY, season INTEGER, body TEXT);
CREATE TABLE games(id INTEGER PRIMARY KEY, season INTEGER, body TEXT);
CREATE TABLE plays(id TEXT PRIMARY KEY, season INTEGER, body TEXT);
CREATE TABLE teams(season INTEGER, id INTEGER, body TEXT, PRIMARY KEY(season,id));
