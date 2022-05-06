from .common import call_endpoint

import urllib 
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from dateutil import parser
from slack_sdk.webhook import WebhookClient

class TimeController():

    def __init__(self, rpc, epoch_start_time, check_interval = 10, new_block_threshold = 30, slack_webhook = None):

        self.rpc = rpc
        self.check_interval = int(check_interval)
        self.new_block_threshold = int(new_block_threshold)
        
        self.node_info = self.get_node_info()
        self.sync_info = None

        self.is_synced = None
        self.is_epoch = False

        self.dt_last_epoch = parser.parse(epoch_start_time)
        self.slack_webhook = slack_webhook

    def get_node_info(self):

        url = urllib.parse.urljoin(self.rpc, "/status")
        response = call_endpoint(url)
        data = response.json()
        return data["result"]["node_info"]
    
    def get_sync_info(self):

        url = urllib.parse.urljoin(self.rpc, "/status")
        response = call_endpoint(url)

        if response.status_code == 200:
            data = response.json()
            return data["result"]["sync_info"]
        else:
            logging.error("Error making the call to {url}".format(url=response.url))

    def set_synced_state(self, state):

        if self.is_synced != state:
            self.is_synced = state
            self.send_alarm()

    async def loop(self):

        while True:
            self.sync_info = self.get_sync_info()

            if self.sync_info["catching_up"]:
                logging.info("🚫 {rpc} not in sync [🏃 catching up]".format(rpc=self.rpc))
                self.set_synced_state(False)

            else:
                # Check time threshold
                latest_block_time = self.sync_info["latest_block_time"]
                latest_block_height = self.sync_info["latest_block_height"]
                dt_latest_block_time = parser.parse(latest_block_time)
                dt_now = datetime.now(timezone.utc)
                seconds_since_latest_block = (dt_now - dt_latest_block_time).total_seconds()
                
                # Node is fetching blocks
                if (seconds_since_latest_block <= self.new_block_threshold):
                    logging.info("✅ {rpc} in sync [ 🕒 {s:.3f}(s) since block {b} ]".format(
                        rpc = self.rpc, 
                        s   = seconds_since_latest_block, 
                        b   = latest_block_height))
                    
                    self.set_synced_state(True)
                    self.is_epoch = False
                
                # Node is not fetching blocks
                else:
                    # Check if it's epoch before updating state
                    dt_current_epoch = self.dt_last_epoch + timedelta(days=1)
                    if dt_latest_block_time >= dt_current_epoch:
                        self.is_epoch = True
                        self.dt_last_epoch = dt_current_epoch
                    else:
                        self.set_synced_state(False)
                        logging.error("🚫 {rpc} not in sync [ 🕒 {s:.3f}(s) since block {b} ]".format(rpc=self.rpc, s=seconds_since_latest_block, b=latest_block_height))

            await asyncio.sleep(self.check_interval)

    def send_alarm(self):

        if not self.slack_webhook:
            return None

        webhook = WebhookClient(self.slack_webhook)

        if not self.is_synced:
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
                                "text": "*Moniker*\n{}".format(self.node_info["moniker"])
                            },
                            {
                                "type": "mrkdwn",
                                "text": "*Network*\n{}".format(self.node_info["network"])
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Last Block Height*\n{height}".format(height=self.sync_info["latest_block_height"])
                            },
                            {
                                "type": "mrkdwn",
                                "text": "*Last Block Time*\n{time}".format(time=self.sync_info["latest_block_time"])
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
                                "text": "*Moniker*\n{}".format(self.node_info["moniker"])
                            },
                            {
                                "type": "mrkdwn",
                                "text": "*Network*\n{}".format(self.node_info["network"])
                            }
                        ]
                    },
                    {
                        "type": "divider"
                    }
                ]
            )
            return response.status_code
