import urllib 
import logging
import asyncio
from datetime import datetime, timezone, timedelta

from dateutil import parser
from slack_sdk.webhook import WebhookClient
from collections import namedtuple
from .common import call_endpoint, parse_sync_info, parse_node_info

Block = namedtuple('Block', 'height time hash')

class TimeController():

    def __init__(self, rpc, check_interval = 10, new_block_threshold = 30, slack_webhook = None):
        self.rpc = rpc
        self.check_interval = int(check_interval)
        self.new_block_threshold = int(new_block_threshold)

        self.moniker, self.node_id, self.network = self.get_node_info()

        self.in_sync = None
        self.last_block = None
        self.cathing_up = None

        self.is_epoch = False
        self.epoch_block = None
        self.dt_last_epoch = parser.parse("2022-05-05T17:16:09.898160996Z") # hardcoded for quick testing
        
        self.slack_webhook = slack_webhook
    
    def check_epoch_start(self):

        dt_last_block = parser.parse(self.last_block.time)
        dt_current_epoch_start = self.dt_last_epoch + timedelta(days=1)

        if dt_last_block >= dt_current_epoch_start:
            self.is_epoch = True
            self.dt_last_epoch = dt_current_epoch_start
            self.epoch_block = self.last_block
    
    def check_epoch_over(self):
        if self.is_epoch and (self.last_block.height > self.epoch_block.height):
            self.is_epoch = False

    def get_node_info(self):
        url = urllib.parse.urljoin(self.rpc, "/status")
        response = call_endpoint(url)     
        return parse_node_info(response.json())   

    def get_sync_info(self):
        url = urllib.parse.urljoin(self.rpc, "/status")
        response = call_endpoint(url)

        if response.status_code == 200:
            self.catching_up, self.last_block = parse_sync_info(response.json())
        else:
            logging.error("Error making the call to {url}".format(url=response.url))

        logging.debug(
            "{rpc} height={h} time={t} hash={hx} catching_up={c}"
            .format(
                rpc=self.rpc,
                h=self.last_block.height, 
                t=self.last_block.time,
                hx=self.last_block.hash,
                c=self.catching_up
            )
        )

    def update_sync_state(self, new_state):
        
        if self.in_sync != new_state:
            self.in_sync = new_state
            self.send_alarm()

    async def loop(self):

        while True:

            self.get_sync_info()
            self.check_epoch_over()
            
            if self.catching_up:
                self.update_sync_state(False)
                logging.info("🚫 {rpc} not in sync [🏃 catching up]".format(rpc=self.rpc))
            else:
                dt_now = datetime.now(timezone.utc)
                dt_last_block = parser.parse(self.last_block.time)
                delta_seconds = (dt_now - dt_last_block).total_seconds()
                
                # Check epoch
                self.check_epoch_start()

                if self.is_epoch:
                    print("EPOCH!")
                    continue
            
                # Update sync state
                self.update_sync_state(delta_seconds <= self.new_block_threshold)

                if self.in_sync:
                    logging.info("✅ {rpc} in sync [ 🕒 {s:.3f}(s) since block {b} ]".format(rpc=self.rpc, s=delta_seconds, b=self.last_block.height))
                else:
                    logging.error("🚫 {rpc} not in sync [ 🕒 {s:.3f}(s) since block {b} ]".format(rpc=self.rpc, s=delta_seconds, b=self.last_block.height))

            await asyncio.sleep(self.check_interval)

    def send_alarm(self):

        if not self.slack_webhook:
            return None

        webhook = WebhookClient(self.slack_webhook)

        if not self.in_sync:
            response = webhook.send(
                text="🚨 alarm",
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "plain_text",
                            "text": "🔄 Node out of sync 🔴",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Moniker*\n{}".format(self.moniker)
                            },
                            {
                                "type": "mrkdwn",
                                "text": "*Network*\n{}".format(self.network)
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Last Block Height*\n{height}".format(height=self.last_block.height)
                            },
                            {
                                "type": "mrkdwn",
                                "text": "*Last Block Time*\n{time}".format(time=self.last_block.time)
                            }
                        ]
                    },
                    {
                        "type": "divider"
                    }
                ]
            )
        else:
            response = webhook.send(
                text="🚨 alarm",
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "plain_text",
                            "text": "🔄 Node back in sync 🟢",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Moniker*\n{}".format(self.moniker)
                            },
                            {
                                "type": "mrkdwn",
                                "text": "*Network*\n{}".format(self.network)
                            }
                        ]
                    },
                    {
                        "type": "divider"
                    }
                ]
            )
            return response.status_code
