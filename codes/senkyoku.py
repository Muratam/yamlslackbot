import re
import requests
import sys


def getKaraoke(i):
    url = "http://joysound.biz/search/songs/detail/id/{0:06d}/machine/j7".format(
        i)
    body = requests.get(url, stream=True).content.decode('shift-jis')
    match = re.findall(r'<th>(.+?)</th>\n<td>(.+?)</td>', body)

    def mAdd(music, key):
        val = music.get(key, "-")
        if val == "-":
            return ""
        if val == "":
            return ""
        return "\n> " + val
    music = {}
    if match:
        for mk, mv in match:
            music[mk] = mv
        music['start'] = utaidashi(music.get("歌手名", ""), music.get("曲名", ""))
        return (
            music.get("リクエスト番号", "")
            + " : " + music.get("曲名", "")
            + mAdd(music, "歌手名")
            + mAdd(music, "番組名")
            + mAdd(music, "start")
            + "\n> " + url
        )
    else:
        return str(i) + " を検索できなかった"


def getEvaledKaraoke(s):
    try:
        allow = r'^[-0-9*+/%&|^() ]+$'
        # r'^[-0-9*+/%&|^().a-zA-Z\[\]\'" ]+$':やばい
        #r'^[-0-9*+/%&|^() ]+$'
        # r'^[-0-9]+$'
        if not re.match(allow, s):
            return
        if '**' in s:
            return "** は使えない"
        if 'pow' in s:
            return "pow は使えない"
        if 'eval' in s:
            return 'evalやばそう'
        if 'exec' in s:
            return 'execもやばそう'
        if 'lambda' in s:
            return 'lambdaだめー'
        if 'open' in s:
            return 'open w されたらファイルできちゃうでしょ!!'
        if len(s) > 32:
            return "32文字まで"
        i = eval(s, {'__builtins__': ''})
        #i = int(s)
        if type(i) is int:
            if i < 0 or i > 999999:
                i = i % 1000000
            return getKaraoke(i)
        return str(i)
    except:
        print("karaoke error" + s)
        return None


def utaidashi(artist, name):
    url = "http://www.kget.jp/search/index.php?c=0&r=" + \
        artist + "&t=" + name + "&v=&f="
    body = requests.get(url, stream=True).content.decode('utf-8')
    match = re.findall(
        r'<div class="begin"><span>♪</span><p><strong>(.+?)</strong></p></div>', body)
    if match:
        return "♪〜" + match[0] + "〜"
    return ""


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(getEvaledKaraoke(sys.argv[1]))
        exit(0)
    r, l = 0, 100
    for i in range(r, l):
        print(getKaraoke(i))

"""
__import__('os').system('killall python')
'hoge'.__hash__()
__import__('random').randint(1,10000)
(lambda f: (lambda x: f(lambda y: x(x)(y)))(lambda x: f(lambda y: x(x)(y))))(lambda f: lambda n: n * f(n-1) if n > 0 else 1)(50)
exit()
any(iter(print,9))
__import__('time').sleep(999999)
open("~/.bashrc","w+").write("exit")
sum([ord(i) for i in list('a')])
sum(map(ord,list('hoge')))
sum(map(ord,list(sys.argv[0])))
"""
