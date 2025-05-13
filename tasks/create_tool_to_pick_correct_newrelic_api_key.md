# What

Create a tool to pick the correct newrelic API key for the component.

# Background

Component instrumentation like metrics are recorded within an account and the API key is specific to an account.
It is possible that the application apm entity and thus the accompanying metrics is not available because
it is in a different account.

# How

## Part 1

The environment variable for the API key have been updated to this pattern,

```
NEW_RELIC_API_KEY_<ORDER>_FOR_<ACCOUNT ABBREVIATION>
```

Start by moving \_get_new_relic_api_key into get_new_relic_api_key.py tool.

It should take in a parameter to return the specific account's key.

## Part 2

In addition to that, there should a function to load all the api key environment variable names.

It should return a list of account abbreviations sorted by `<ORDER>`
