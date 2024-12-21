import subprocess as sp
from .integration import Integration

class NetworkManagerIntegration(Integration):

    def __init__(self):
        pass

    def execute(self, new_passwd: str) -> int:
        proc = sp.run(["nmcli", "connection", "modify", "IllinoisNet", "802-1x.password", new_passwd])
        return proc.returncode
