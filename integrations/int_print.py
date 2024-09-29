from .integration import Integration

class PrintIntegration(Integration):
    def execute(self, new_passwd: str):
        print(f"""

====== Your New Password ======
                       
       {new_passwd}

===============================

""")
