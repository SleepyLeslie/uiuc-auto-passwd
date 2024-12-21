from .integration import Integration

class PrintIntegration(Integration):

    def __init__(self):
        pass

    def execute(self, new_passwd: str) -> int:
        print(f"""

====== Your New Password ======
                       
       {new_passwd}

===============================

""")
        return 0
