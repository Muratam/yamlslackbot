import time
import os.path
import requests
from slackclient import SlackClient
from pprint import pprint
from multiprocessing import Process
import slacklog

class Slack72:

    def __init__(self, token):
        self._token = token
        self._slack = SlackClient(self._token)
        self._channels = {}
        self._channels_time = 0
        self._channel_members = {}
        self._users = {}
        self._users_time = 0

    def post_message(self, postData={}):
        return requests.post(
            "https://slack.com/api/chat.postMessage",
            data=dict(postData, token=self._token)
        )

    # tablenameを指定して、func(:dict) な関数を呼び、結果を更新する
    def update(self, tablename, func):
        dic = slacklog.get_dict(tablename)
        res = func(dic) or ""
        slacklog.set_dict(tablename, dic)
        return res

    def update_channels(self, ID,force=False):
        if not force and ID in self._channels:
            self._channels_time += 1
            if self._channels_time < 300:
                return  # 300回くらい来たらやっぱり最新のに更新する
        info = self._slack.api_call("channels.list")
        if info.get("ok"):
            self._channels_time = 0
            self._channels = {}
            channels = []
            for channel in info["channels"]:
                cid = channel["id"]
                self._channels[cid] = channel
                self._channel_members[cid] = channel.get("members",[])
                channels.append([
                    channel["id"],
                    "#" + channel["name"],
                    channel["topic"]["value"]
                ])                    
            slacklog.make_data(channels, ["channel", "name","topic"], "channel")
        else:
            raise Exception("CA'NT CONNECT EXCEPTION")

    def update_users(self, ID, force=False):
        if not force and ID in self._users:
            self._users_time += 1
            if self._users_time < 300:
                return  # 300回くらい来たらやっぱり最新のに更新する
        if not ID.startswith("U"): return
        info = self._slack.api_call("users.list", user=ID)
        if info.get("ok"):
            self._users = {}
            self._users_time = 0
            members = []
            for user in info["members"]:
                self._users[user["id"]] = user
                members.append([user["id"], user["name"], user.get("profile",{}).get("image_72","")])
            slacklog.make_data(members, ["user", "name","image"], "user")

    def get_channel_name(self, ID):
        self.update_channels(ID)
        return "#" + self._channels[ID]["name"]

    def get_user_name(self, ID):
        self.update_users(ID)
        return self._users.get(ID,{}).get("name", "")

    def get_uid_by_name(self,name):
        if not self._users : return ""
        return {v.get("name",""):k for k,v in self._users.items()}.get(name,"")

    def get_user_image(self, ID):
        self.update_users(ID)
        return self._users.get(ID, {}).get("profile", {}).get("image_48")

    def get_user_title(self, ID):
        self.update_users(ID, True)
        title = self._users.get(ID, {}).get("profile", {}).get("title", "")
        return "[" + title + "]" if title else ""

    def is_collect_message(self, info):
        if info.get("subtype", "") == "message_changed":
            return self.get_previous_message(info) != self.get_text(info)
        return True

    def get_uid(self, info):
        return info.get("user", "") or info.get("message", {}).get("user", "")

    def get_joining_channels_by_uid(self,uid):
        self.update_channels("",True)
        res = []
        for cid,members in self._channel_members.items():
            if not uid in members: continue
            if not cid in self._channels:continue
            res.append("#" + self._channels[cid]["name"])
        return res

    def _update_topic(self,_new_topic,channel):
        _old_topic = self._channels[channel]["topic"]["value"]
        self._channels[channel]["topic"]["value"] = _new_topic
        return _old_topic

    def is_editted_message(self, info):
        if info.get("subtype", "") != "message_changed":
            return False
        return self.get_previous_message(info) != self.get_text(info)

    def is_bot_message(self, info):
        uid = self.get_uid(info)
        self.update_users(uid)
        if info.get("subtype", "") == "bot_message":
            return True
        if "bot_id" in info:
            return True
        return self._users.get(uid, {}).get("is_bot", False)

    def get_previous_message(self, info):
        return info.get("previous_message", {}).get("text", "")

    def get_text(self, info):
        text = info.get("text", "")
        if text:
            return text
        if len(info.get("attachments", [])) > 0:
            return (info["attachments"][0].get("text") or info["attachments"][0].get("pretext"))
        return info.get("message", {}).get("text", "")


    def process_message(self, info):
        channel = self.get_channel_name(info.get("channel", ""))
        text = self.get_text(info)
        if self.is_bot_message(info):
            username = info.get("username", "UNKNOWN_BOT")
            icon_url = info.get("icons", {}).get("image_48", "no_image")
            self.received_bot_message(info, username, icon_url, channel, text)
        else:
            uid = self.get_uid(info)
            if not uid:
                return None
            username = self.get_user_name(uid)
            icon_url = self.get_user_image(uid)
            if self.is_collect_message(info):
                self.received_message(info, username, icon_url, channel, text)

    def process_add_reaction(self, info):
        channel = info.get("item", {}).get("channel", "")
        ts = info.get("item", {}).get("ts", "")
        history = self._slack.api_call("channels.history", channel=channel)
        if not history.get("ok"):
            raise Exception("CANT GET HISTORY EXCEPTION")
        messages = history.get("messages", [])
        for message in messages:
            if ts != message.get("ts"):
                continue
            username = (self.get_user_name(message.get("user", ""))
                        or message.get("username", ""))
            icon_url = (self.get_user_image(message.get("user", ""))
                        or message.get("icons", {}).get("image_48", ""))
            text = (message.get("text", "")
                    or message.get("attachments", [{}])[0].get("text", ""))
            reaction = info.get("reaction", "")
            channel = self.get_channel_name(channel)
            addedusers = []
            for r_info in message.get("reactions", [{}]):
                if r_info.get("name", "") == reaction:
                    addedusers = r_info.get("users", [])
            if not addedusers:
                raise Exception("NO ADDED USERS EXCEPTION")
            addedusers = [self.get_user_name(_) for _ in addedusers]
            return self.received_add_reaction(info, username, icon_url, channel, text, ":" + reaction + ":", addedusers)

    def parse_info(self,info):
        info_type = info.get("type", "")
        info_subtype = info.get("subtype", "")
        # ignore trivial information
        if info_type in ["", "presence_change", "user_typing", "reconnect_url","pref_change"]:
            return
        # hook user_change event
        if info_type == "user_change":
            self.user_change(info)
        # hook channel_topic change event :: ignore other channel events
        if info_subtype.startswith("channel") or info_type.startswith("channel"):
            if info_subtype != "channel_topic":
                return
            else :
                info["old_topic"] = self._update_topic(info["topic"],info["channel"])
        # allow only message_changed event :: ignore other hidden events
        if info.get("hidden") :
            if info_subtype != "message_changed":
                return
            # 謎の message_changed な file_share が存在するので無視
            if info.get("message", {}).get("subtype", "") == "file_share":
                return
        # ignore thread events
        if info.get("thread_ts"):
            return
        # ignore private group (G*****)
        if not info.get("channel","G").startswith("C") :
            return
        # finally !!
        if info_type == "message":
            self.process_message(info)
        elif info_type == "reaction_added":
            self.process_add_reaction(info)
        return True

    def logging(self,info):
        if ("ts" not in info ) or ("channel" not in info):
            return
        Process(
            target=slacklog.log_slack,
            args= ({
                "ts":info["ts"],
                "text":self.get_text(info),
                "user":self.get_uid(info) or "U0797L6LD",
                "channel":info["channel"]
            },)
        ).start()


    def connect(self, logging=True):
        if not self._slack.rtm_connect():
            raise Exception("CANT CONNEXT TO SLACK ...")
        print("connecting...")
        for i in range(5):
            time.sleep(1)
            self._slack.rtm_read()
        print("connected to slack")
        self.first_connect()
        while True:
            infos = self._slack.rtm_read()
            if infos == []:
                time.sleep(1)
                continue
            for info in infos:
                successed = self.parse_info(info)
                if not successed :
                    continue
                print(info)
                if logging:
                    self.logging(info)


    def first_connect(self):
        pass

    def received_bot_message(self, info, username, icon_url, channel, text):
        pass

    def received_message(self, info, username, icon_url, channel, text):
        pass

    def received_add_reaction(self, info, username, icon_url, channel, text, reaction, addedusers):
        pass

    def user_change(self,info):
        pass


if __name__ == "__main__":
    if not os.path.isfile("SLACK_TOKEN"):
        raise Exception("NO SLACK TOKEN FILE EXCEPTION!!")
    with open("SLACK_TOKEN") as f:
        TOKEN = f.read()
    slack = Slack72(TOKEN)
    slack.connect()
