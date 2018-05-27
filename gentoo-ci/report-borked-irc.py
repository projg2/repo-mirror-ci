#!/usr/bin/env python

import os.path
import sys
import time

import irc.client


class Croaker(irc.client.SimpleIRCClient):
    def __init__(self, channel, people, url, commit_urls):
        super(Croaker, self).__init__()
        self.channel = channel
        self.people = people
        self.url = url
        self.commit_urls = commit_urls

    def on_welcome(self, connection, event):
        connection.join(self.channel)

    def on_join(self, connection, event):
        message = ["Oh no! Gentoo is broooken!"]
        if self.people:
            message[0] += " %s, you broke it!" % (', '.join(x.split('@')[0] for x in self.people))
        message.append('Report: %s' % self.url)
        for c in self.commit_urls[:4 if len(self.commit_urls) <= 4 else 3]:
            message.append(c)
        if len(self.commit_urls) > 4:
            message.append('(and %d more commits)' % (len(self.commit_urls) - 3))

        time.sleep(3)
        for l in message:
            self.connection.privmsg(self.channel, l)
            time.sleep(0.75)
        time.sleep(5)
        self.connection.quit("[repo-mirror-ci croaker bot]")

    def on_disconnect(self, connection, event):
        sys.exit(0)


def main(people, url, commit_urls):
    server = os.environ['IRC_SERVER']
    port = int(os.environ['IRC_PORT'])
    nick = os.environ['IRC_NICKNAME']
    pass_file = os.environ['IRC_PASSWORD_FILE']
    channel = os.environ['IRC_CHANNEL']

    with open(os.path.expanduser(pass_file), 'r') as f:
        password = f.read().strip()

    c = Croaker(channel, people.split(), url, commit_urls.split())
    c.connect(server, port, nick, password)
    c.start()


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
