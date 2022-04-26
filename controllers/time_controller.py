import urllib 
import logging
import asyncio
from datetime import datetime, timezone

from dateutil import parser

from collections import namedtuple
from .common import call_endpoint, parse_sync_info

Block = namedtuple('Block', 'height time hash')

class TimeController():

    def __init__(self, rpc, check_interval = 10, new_block_threshold = 30):
        self.rpc = rpc
        self.check_interval = int(check_interval)
        self.new_block_threshold = int(new_block_threshold)

        self.in_sync = None
        self.last_block = None
        self.cathing_up = None
    
    def update_sync_info(self):
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

    async def loop(self):

        while True:
            self.update_sync_info()
            
            if self.catching_up:
                self.in_sync = False
                logging.info("🚫 {rpc} not in sync [🏃 catching up ]")
            else:
                dt_now = datetime.now(timezone.utc)
                dt_last_block = parser.parse(self.last_block.time)
                delta_seconds = (dt_now - dt_last_block).total_seconds()

                self.in_sync = delta_seconds <= self.new_block_threshold

                if self.in_sync:
                    logging.info("✅ {rpc} in sync [ 🕒 {s:.3f}(s) since block {b} ]".format(rpc=self.rpc, s=delta_seconds, b=self.last_block.height))
                    
                else:
                    logging.error("🚫 {rpc} not in sync [ 🕒 {s:.3f}(s) since block {b} ]".format(rpc=self.rpc, s=delta_seconds, b=self.last_block.height))

            await asyncio.sleep(self.check_interval)
