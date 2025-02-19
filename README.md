# State2Slack

State2Slack fetches the state of a Home Assistant entity, translates the state value into a designated Slack channel and message, and delivers the message accordingly. Additionally, a confirmation message detailing the completion and outcomes is sent to a Slack user.

Log files record the completion history for a given day and ensure tasks are not re-executed within the same day.

## ⚙️ Configuration

The following configuration is to be provided in the file `config.yaml`

```yaml
---

# The configuration for Home Assistant requests.
home_assistant:
  # The URL of Home Assistant.
  url:

  # The access token for authentication.
  token:

  # The entity ID to trigger based on state.
  entity_id:

  # (Optional) True to ignore verifying the SSL certificate.
  insecure: false

# The configuration for Slack channel message requests.
slack_channels:
  # The default, fallback, configuration.
  default:
    # The webhook URL to send messages to a channel.
    url:

    # The channel ID to send the messages to.
    channel:

    # The message to send to the channel.
    message:

# Custom Home Assistant entity state values, as lowercase.
# The following example uses 'work' but any word value is accepted.
# work:
#   url:
#   channel:
#   message:

# The configuration for Slack user message requests.
slack_user:
  # The webhook URL to send messages to a user.
  url:

  # The user ID of the recipient of the messages.
  user_id:
```

## 🚀 Usage

To execute the task

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
