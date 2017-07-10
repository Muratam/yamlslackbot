import sqlite3
import pandas as pd
import pandas.io.sql as psql
import ast
import hashlib
import sys
import random
from sqlalchemy import create_engine
import sqlalchemy.types as dtype
import requests
# message: |channel|user|text|  <= ts
# coin : val <= username

slack_columns = ["ts", "text", "user", "channel"]
slack_types = dict(zip(slack_columns, [
    lambda x: int(x.replace(".", "")), str, str, str
]))
slack_columns_types = dict(zip(slack_columns, [
    dtype.INT(), dtype.TEXT(), dtype.NVARCHAR(length=9), dtype.NVARCHAR(length=9)
]))
slack_db_name = "all.db"
gacha_required_jewel = 100

def parse_dict(dic, columns=slack_columns, types=slack_types):
    res = []
    for column in columns:
        if column not in dic:
            return None
        res.append(types[column](dic[column]))
    return res


def log2dataframe(filename):
    def is_prettyprint(l):
        start = l.startswith(" ") or l.startswith("{")
        end = l.endswith(",\n") or l.endswith("'\n") or l.endswith("\"\n")
        return start and end
    datas = []
    with open(filename) as f:
        chunkline = ""
        for line in f.readlines():
            if is_prettyprint(line):
                chunkline += line
                continue
            if chunkline:
                if line.startswith("{"):
                    chunkline = ""
                line = chunkline + line
                chunkline = ""
            else:
                if not line.startswith("{"):
                    continue
                if not line.endswith("}\n") and not line.endswith("}"):
                    continue
            try:
                data = parse_dict(ast.literal_eval(line), slack_columns)
                if data:
                    datas.append(data)
            except Exception as e:
                print("############ERROR#############")
                print(e)
                print(line)
    return datas


def add_dataframe(conn, df, tablename="message"):
    if conn.has_table(tablename):
        # そのtsがすでにあるかチェック
        ts = str(df["ts"][0])
        a = conn.execute("select count(*) from %s where ts=?" % tablename, ts)
        if a.fetchone()[0]:
            return
    psql.to_sql(df, "message", conn, index=False,
                if_exists="append", dtype=slack_columns_types)


def log_slack(info):
    try:
        conn = create_engine("sqlite:///" + slack_db_name)
        data = parse_dict(info, slack_columns, slack_types)
        if not data:
            return
        data = [data]
        df = pd.DataFrame(data, columns=slack_columns, index=None)
        add_dataframe(conn, df, "message")
    except Exception as e:
        print("LOG ERROR")
        print(e)

def get_dict(tablename):
    conn = create_engine("sqlite:///" + slack_db_name)
    if not conn.has_table(tablename):
        return {}
    df = psql.read_sql("select * from %s" % tablename, conn)
    res = {}
    for _, v in df.iterrows():
        res[v[0]] = v[1]
    return res


def set_dict(tablename, dic):
    conn = create_engine("sqlite:///" + slack_db_name)
    data = []
    for k, v in dic.items():
        data.append([k, v])
    make_data(data, ["k", "v"], tablename)


def make_data(datas, columns, tablename):
    if tablename == "message":
        print("CANT USE SLACK LOG TABLE!!")
        return
    try :
        conn = create_engine("sqlite:///" + slack_db_name)
        df = pd.DataFrame(datas, columns=columns, index=None)
        psql.to_sql(df, tablename, conn, index=False, if_exists="replace")
    except Exception as e:
        print("############ERROR#############")
        print(e)

def get_data(tablename):
    conn = create_engine("sqlite:///" + slack_db_name)
    if not conn.has_table(tablename):
        return []
    df = psql.read_sql("select * from %s" % tablename, conn)
    res = []
    for k, v in df.iterrows():
        res.append(v.tolist())
    return res


if __name__ == "__main__":
    conn = create_engine("sqlite:///" + slack_db_name)
    count = psql.read_sql("select count(*) from message", conn).loc[0][0]
    print("{} messages exists".format(count))
