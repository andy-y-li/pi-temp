PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE temps(
    name DEFAULT 'RPi.CPU',
    tdatetime DATETIME DEFAULT (datetime('now', 'localtime')),
    temperature NUMERIC NOT NULL,
    fan NUMERIC NOT NULL
);
COMMIT;
