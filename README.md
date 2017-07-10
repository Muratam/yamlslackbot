# description
Yaml customizable python slack Bot.
Automatic save messages using SQLite !!
Write bot code in codes/**.py



# TRY THIS BOT

```sh
$ pip3 install -r requirements.txt
$ echo "xoxp-****" > SLACK_TOKEN
$ python3 yamlbot.py template.yml
```

# USE yamlbot as module
```sh
$ echo "from yamlbot import YamlBot\n YamlBot('hoge.yml').connect()" > hoge.py
$ echo "...." > hoge.yml
$ mkdir codes && echo "...." > plugin.py
$ python3 hoge.py
```


# yaml memo

- important !! '<< >>' is expanded and evaled as python3 script
- variables ::text,channel,username,icon_url,info, (match)

| tag | information | default |
|:--|:--|:--|
|`find`| reqular expression OK (capture result => variable `match`) | `.*`|
|`to`  | submitting channel | `<<channel>>`(same channel)|
|`from` | reqcting channels | `.*` (allow all channels )|
|`username` | bot name | `<<username>>` (same name)|
|`icon_url` | bot icon | `<<icon_url>>` (same icon)|
|`text` | bot text | `"<<"｀"+channel+"｀ " + text>>"` (channelname and text)|
