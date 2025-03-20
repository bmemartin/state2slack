# State2Slack

State2Slack automates Slack message posting based on the state of a Home Assistant entity.

It retrieves an entity's state and maps it to a configurable Slack webhook URL, message, and optional target ID. These values are then used to send a message to Slack via a webhook request. If configured, a summary of the execution results is sent to a designated Slack webhook.

Log files track execution history and, if maintained, prevent re-execution within the same day.

## ⚙️ Configuration

Configuration is provided through a YAML file. Unless specified via command-line options, State2Slack defaults to using `config.yaml`.

```yaml
---

# The configuration for Home Assistant requests.
home_assistant:
  # The URL of Home Assistant.
  url:

  # The long-lived access token for authentication.
  access_token:

  # The entity ID to trigger based on state.
  entity_id:

  # (Optional) True to ignore verifying the SSL certificate.
  insecure: false

# The configuration for Slack state message issuance.
slack_states:
  # One or more `ENTITY_STATE` entries representing lowercase entity state values.
  # Use `default` to specify a fallback scenario.
  ENTITY_STATE:
    # The webhook URL for sending state messages.
    webhook_url:

    # The message content.
    message:

    # (Optional) The target ID of the message recipient.
    target_id:

# (Optional) The configuration for Slack summary message issuance.
slack_summary:
  # The webhook URL for sending summary messages.
  webhook_url:

  # (Optional) The target ID of the message recipient.
  target_id:
```

## 🚀 Usage

To execute the automation

```shell
python3 state2slack.py
```

To review command line options

```shell
python3 state2slack.py --help
```

## 🐳 Container

To build the container image

```shell
docker compose build
```

To run the container

```shell
docker compose run --rm state2slack
```

To run the container with command line options

```shell
docker compose run --rm state2slack python3 state2slack.py --log DEBUG
```
