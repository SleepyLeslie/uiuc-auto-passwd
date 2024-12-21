import subprocess as sp
import configparser
import json
import base64
import os
from .integration import Integration
from logger import logger

class BitwardenIntegration(Integration):

    def __init__(self, config: configparser.SectionProxy):
        self.retry = config.getint("retry", 3)
        if (ids := config.get("ids")) is None:
            logger.warning("No item IDs specified.")
            self.ids = []
        else:
            self.ids = ids.split(" ")

    def execute(self, new_passwd: str) -> int:
        if len(self.ids) == 0:
            return 0
        bw_status_proc = sp.run(["bw", "status"], stdout=sp.PIPE)
        bw_status = json.loads(bw_status_proc.stdout)
        match bw_status["status"]:
            case "locked":
                for _ in range(self.retry):
                    unlock_proc = sp.run(["bw", "unlock"], stdout=sp.PIPE)
                    if unlock_proc.returncode == 0:
                        logger.info("Unlocked Bitwarden vault.")
                        os.environ["BW_SESSION"] = unlock_proc.stdout.decode().split("\n")[-1].split(" ")[-1]
                        break
                    logger.warning("Failed to unlock Bitwarden vault, try again.")
            case "unlocked":
                pass
            case _:
                logger.warning("Bitwarden vault not ready, update skipped.")
                return 1
        ret = 0
        for item_id in self.ids:
            logger.info("Updating Bitwarden item %s...", item_id)
            get_item_proc = sp.run(["bw", "get", "item", item_id], stdout=sp.PIPE)
            if get_item_proc.returncode != 0:
                logger.warning("Failed to retrieve item %s.", item_id)
                ret += 1
                continue
            item = json.loads(get_item_proc.stdout)
            item_name = item["name"]
            item["login"]["password"] = new_passwd
            update_proc = sp.run(["bw", "edit", "item", item_id],
                                 input=base64.b64encode(json.dumps(item).encode()), stdout=sp.PIPE)
            if update_proc.returncode != 0:
                logger.warning("Failed to update password for item %s.", item_name)
                ret += 1
            else:
                logger.info("Updated password for item %s.", item_name)
        return ret
