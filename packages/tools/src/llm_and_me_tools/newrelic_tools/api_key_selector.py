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
    Retrieves the New Relic API key from an account-specific environment variable
    matching the pattern NEW_RELIC_API_KEY_<ORDER>_FOR_<ACCOUNT_ABBREVIATION_UPPERCASE>.

    The function searches environment variables for a key that starts with
    'NEW_RELIC_API_KEY_', ends with '_FOR_' followed by the uppercase account
    abbreviation, and has an <ORDER> string between the prefix and suffix.
    For example, NEW_RELIC_API_KEY_1_FOR_MYACC.

    If the 'account' parameter is not provided or is an empty string, or if no API key
    is found for the specified account matching the pattern, it raises a ValueError.

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

    account_upper = account.upper()
    expected_suffix = f"_FOR_{account_upper}"

    for var_name, api_key_value in os.environ.items():
        if var_name.startswith(ACCOUNT_SPECIFIC_API_KEY_ENV_VAR_PREFIX) and \
           var_name.endswith(expected_suffix):
            # Extract the part that should be <ORDER>
            # e.g., NEW_RELIC_API_KEY_  <ORDER>  _FOR_ACCOUNTNAME
            #        ^--prefix          ^order^   ^--suffix
            prefix_len = len(ACCOUNT_SPECIFIC_API_KEY_ENV_VAR_PREFIX)
            suffix_len = len(expected_suffix)
            
            # Ensure there's content between prefix and suffix for <ORDER>
            if len(var_name) > prefix_len + suffix_len:
                # order_part = var_name[prefix_len : len(var_name) - suffix_len]
                # We just need to ensure this part exists, the actual value of order
                # is not used for selection in this function, only that it matches the pattern.
                return api_key_value

    raise ValueError(
        f"New Relic API key not found for account '{account}'. "
        f"Ensure an environment variable matching the pattern "
        f"'{ACCOUNT_SPECIFIC_API_KEY_ENV_VAR_PREFIX}<ORDER>{expected_suffix}' is set."
    )
