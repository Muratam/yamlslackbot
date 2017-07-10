from slack72 import Slack72
import re
import os.path
import json
import yaml
import sys
import emoji
import slacklog
from multiprocessing import Process


class YamlBot(Slack72):

    def __init__(self,yamlpath):
        with open(yamlpath, encoding="utf-8") as f:
            self.yaml = next(yaml.load_all(f))
        tokenfile = self.yaml.get("tokenfile")
        assert tokenfile , "please set tokenfile parameter in yamlfile !!"
        assert os.path.isfile(tokenfile), tokenfile + " is not file !!"
        with open(tokenfile) as f:
            token = f.read().strip()
        super().__init__(token)


    def filter(self, action, channel, text):
        if not re.match(action.get("from", channel), channel, re.I):
            return False
        if channel == action.get("to", ""):
            return False
        if "find" in action:
            return re.findall(action["find"], text, re.DOTALL)
        return True

    def received_message(self, info, username, icon_url, channel, text):
        if self.is_muted_user(username):
            return
        if self.is_ignored_channel(channel):
            return
        def target(action, info, username, icon_url, channel, text):
            match = self.filter(action, channel, text)
            if match:
                self.post_to_slack(action, icon_url, username,
                                   channel, text, info, match)
        for action in self.yaml.get("actions", []):
            #target(action,info,username,icon_url,channel,text)
            Process(target=target,
                    args=(action, info, username, icon_url, channel, text)).start()

    def received_add_reaction(self, info, username, icon_url, channel, text, reaction, addedusers):
        if len(addedusers) != 1:
            return  # リアクション追加時の最初の一人目のみ
        for add_reaction in self.yaml.get("addReactions", []):
            if add_reaction.get("to", "") == channel:
                continue
            if ("by" in add_reaction) and (add_reaction["by"] != reaction):
                continue
            # print(addReaction)
            self.post_to_slack(
                add_reaction, icon_url, username, channel, text, info, [],
                reaction=reaction, addedusers=addedusers)

    def received_bot_message(self, botInfo, username, icon_url, channel, text):
        def target(action, botInfo, username, icon_url, channel, text):
            if action.get("username", "") == username:
                return
            match = self.filter(action, channel, text)
            if match:
                self.post_to_slack(action, icon_url, username,
                                   channel, text, botInfo, match)
        for action in self.yaml.get("actionsByBotMessage", []):
            Process(target=target,
                    args=(action, botInfo, username, icon_url, channel, text)
                    ).start()

    def is_muted_user(self, name):
        return (name in self.yaml.get("muteUser", []))

    def is_ignored_channel(self,channel):
        return (channel in self.yaml.get("ignoreChannels",[]))

    def first_connect(self):
        for connect in self.yaml.get("firstConnect", []):
            self.post_to_slack(connect)

    def post_to_slack(self, data, icon_url="", username="BOT", channel="", text="", info={}, match=[], **args):
        post_data = data.copy()

        # import modules from imports parameter
        codes_path = os.path.dirname(os.path.abspath(__file__)) + "/codes"
        if codes_path not in sys.path:
            sys.path.append( codes_path )
        for module in self.yaml.get("imports",[]):
            exec("import " + module)
        for k, v in [
                ("link_names", "1"),
                ("to", channel),
                ("username", username),
                ("icon_url", icon_url),
                ("text", self.default_text(text, channel))]:
            post_data[k] = data.get(k, v)
        for k, v in post_data.items():
            expr = re.findall(r'<<(.+)>>', v, re.DOTALL)
            if expr:
                post_data[k] = str(eval(expr[0]))
        post_data["channel"] = post_data["to"]
        post_data["username"] = emoji.emojize(post_data["username"], True)
        if "attachments" in data:
            del post_data["text"]
            attachments = eval(post_data["attachments"])
            for attachment in attachments:
                post_data["attachments"] = json.dumps([attachment])
                print(post_data)
                self.post_message(post_data)
            return
        if not post_data["text"]:
            return
        print("---POST---")
        print(post_data)
        self.post_message(post_data)

    def escape_uid(self, text):
        res = text.replace("!", "！")
        res = res.replace("@", "＠")
        for found in re.findall(r'<＠(.*?)>', res):
            res = res.replace(found, self.get_user_name(found))
        return res

    def default_text(self, text, channel):
        return "`" + channel + "` " + self.escape_uid(text)


if __name__ == "__main__":
    assert len(sys.argv) > 1 , "argmument <yaml-path> is not configured!! \n  ex) $python3 yamlbot.py slack.yml"
    slack = YamlBot(sys.argv[1])
    slack.connect(logging=slack.yaml.get("logging", True))
