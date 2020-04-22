#!/bin/sh
DBNAME="cpu.db"
rm -f $DBNAME
echo 开始插入数据
sqlite3 $DBNAME < create-table-only.sql
echo 插入完成
