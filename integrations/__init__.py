from .int_network_manager import NetworkManagerIntegration
from .int_print import PrintIntegration
from .int_bitwarden import BitwardenIntegration

AVAILABLE_INTEGRATIONS = {
    "print": PrintIntegration,
    "network_manager": NetworkManagerIntegration,
    "bitwarden": BitwardenIntegration
}
