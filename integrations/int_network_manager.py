import subprocess as sp
from .integration import Integration

class NetworkManagerIntegration(Integration):
    def execute(self, new_passwd: str):
        sp.run(["nmcli", "connection", "modify", "IllinoisNet", "802-1x.password", new_passwd])
