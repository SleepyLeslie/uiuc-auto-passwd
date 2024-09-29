from .int_network_manager import NetworkManagerIntegration
from .int_print import PrintIntegration

AVAILABLE_INTEGRATIONS = {
    "print": PrintIntegration,
    "network_manager": NetworkManagerIntegration
}
