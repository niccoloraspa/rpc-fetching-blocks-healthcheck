import os
import logging
import asyncio
from fastapi import FastAPI, Response, status, HTTPException

from controllers.time_controller import TimeController

# DEFAULT values for the parameters
DEFAULT_CHECK_INTERVAL = 10
DEFAULT_NEW_BLOCK_THRESHOLD = 30
DEFAULT_LOG_LEVEL = "INFO"

# RPC_NODE: url of the rpc nodes to check if it's fetching blocks
RPC_NODE = os.environ['RPC_NODE']

# LAST_EPOCH_START_TIME: Time at which last epoch started (format "2021-06-18T17:00:00Z")
LAST_EPOCH_START_TIME = os.environ['LAST_EPOCH_START_TIME']

# SLACK_WEBHOOK: slack incoming webhook to send alerts
SLACK_WEBHOOK = os.getenv('SLACK_WEBHOOK')

# CHECK_INTERVAL: How often should I check
CHECK_INTERVAL = os.getenv('CHECK_INTERVAL', DEFAULT_CHECK_INTERVAL)

# NEW_BLOCK_THRESHOLD: how many seconds should I wait before reporting node as unsynced
NEW_BLOCK_THRESHOLD = os.getenv('FUNCTION', DEFAULT_NEW_BLOCK_THRESHOLD)

# LOG_LEVEL: log level verbosity {INFO, DEBUG}
LOG_LEVEL = os.getenv('LOG_LEVEL', DEFAULT_LOG_LEVEL)

LOG_LEVEL_DICT = {
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}

logging.basicConfig(format='%(levelname)s: %(asctime)s - %(message)s', level=LOG_LEVEL_DICT[LOG_LEVEL])

app = FastAPI()

controller = TimeController(
    rpc = RPC_NODE,
    epoch_start_time = LAST_EPOCH_START_TIME,
    check_interval = CHECK_INTERVAL,
    new_block_threshold = NEW_BLOCK_THRESHOLD,
    slack_webhook = SLACK_WEBHOOK
)

@app.on_event('startup')
async def app_startup():

    logging.info("-"*60)
    logging.info("🛸 Starting controller")
    logging.info("")
    logging.info("RPC_NODE:            {}".format(RPC_NODE))
    logging.info("CHECK_INTERVAL:      {}[s]".format(CHECK_INTERVAL))
    logging.info("NEW_BLOCK_THRESHOLD: {}[s]".format(NEW_BLOCK_THRESHOLD))
    logging.info("-"*60)
    logging.info("")

    asyncio.create_task(controller.loop())

@app.get("/")
def healthcheck():
    if not controller.in_sync:
        raise HTTPException(status_code=503, detail="Node not in sync")
    return controller.in_sync