import os
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file, if present
load_dotenv()

# Standard environment variable name for a single, primary API key
PRIMARY_API_KEY_ENV_VAR = "NEW_RELIC_API_KEY"
# Prefix for account-specific API key environment variables (e.g., NEW_RELIC_API_KEY_ACCOUNT1)
ACCOUNT_SPECIFIC_API_KEY_ENV_VAR_PREFIX = "NEW_RELIC_API_KEY_"


def get_new_relic_api_key(account: str) -> str:
    """
    Retrieves the New Relic API key from an account-specific environment variable.

    The function looks for an environment variable named
    NEW_RELIC_API_KEY_<ACCOUNT_ABBREVIATION_UPPERCASE>.

    If the 'account' is not provided, is an empty string, or if the API key
    is not found for the specified account, it raises a ValueError.

    Args:
        account: A string representing the account abbreviation (e.g., "ACC1",
                 "MYACCOUNT") for which an API key is configured.
                 The abbreviation will be converted to uppercase.

    Returns:
        The New Relic API key.

    Raises:
        ValueError: If the account string is empty or if no API key is found
                    for the specified account in the environment variables.
    """
    if not account or not account.strip():
        raise ValueError(
            "The 'account' parameter cannot be None or an empty string. "
            "Please provide a valid account abbreviation."
        )

    account_specific_var_name = (
        f"{ACCOUNT_SPECIFIC_API_KEY_ENV_VAR_PREFIX}{account.upper()}"
    )
    api_key: Optional[str] = os.getenv(account_specific_var_name)

    if not api_key:
        raise ValueError(
            f"New Relic API key not found for account '{account}'. "
            f"Set the {account_specific_var_name} environment variable."
        )
    return api_key
