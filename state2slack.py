import datetime
import logging
import os
import requests
import yaml

from argparse import ArgumentParser
from dacite import from_dict
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class HomeAssistant:
    """The configuration for Home Assistant requests.

    Attributes:
        url (str): The URL of Home Assistant.
        access_token (str): The long-lived access token for authentication.
        entity_id (str): The entity ID to trigger based on state.
        insecure (bool, optional): True to ignore verifying the SSL certificate, False otherwise. Defaults to False.
    """
    url: str
    access_token: str
    entity_id: str
    insecure: bool = False


@dataclass
class SlackChannel:
    """The configuration for Slack channel message requests.

    Attributes:
        url (str): The webhook URL to send messages to a channel.
        channel (str): The channel ID to send the messages to.
        message (str): The message to send to the channel.
    """
    url: str
    channel: str
    message: str


@dataclass
class SlackUser:
    """The configuration for Slack user message requests.

    Attributes:
        url (str): The webhook URL to send messages to a user.
        user_id (str): The user ID of the recipient of the messages.
    """
    url: str
    user_id: str


@dataclass
class Config:
    """The project configuration.

    Attributes:
        home_assistant (HomeAssistant): The Home Assistant configuration.
        slack_channels (dict[str, SlackChannel]): The Slack channel configuration.
        slack_user (SlackUser): The Slack user configuration.
    """
    home_assistant: HomeAssistant
    slack_channels: dict[str, SlackChannel]
    slack_user: SlackUser

    def slack_channel(self, value: str) -> SlackChannel:
        """Returns the SlackChannel object corresponding to the given value.
        If no SlackChannel object exists for the given value, the default SlackChannel object is returned.

        Args:
            value (str): The value to search for in the SlackChannel objects.

        Returns:
            SlackChannel: The SlackChannel object corresponding to the given value, or the default SlackChannel object if no match is found.
        """
        return self.slack_channels.get(str(value).lower(), self.slack_channels.get('default'))


def parse_args():
    """Parse command line strings into Python objects.

    Returns:
        args: the parsed command line arguments
    """
    parser = ArgumentParser(description='')
    parser.add_argument('--config',
                        type=str,
                        default='config.yaml',
                        help='path to configuration file (default: config.yaml)')
    parser.add_argument('--log', type=str, default='INFO', help='log level for logger (default: INFO)')
    parser.add_argument('--state', type=str, help='override for entity state')
    return parser.parse_args()


def init_logger(directory: str, filename: str, level: str = 'INFO') -> bool:
    """Initialize a logger with a file handler and a stream handler.

    Args:
        directory (str): The directory path where the log file will be created.
        filename (str): The name of the log file.
        level (str, optional): The logging level. Defaults to 'INFO'.

    Returns:
        bool: True if the log file already exists, False otherwise.
    """
    os.makedirs(directory, exist_ok=True)
    file = os.path.join(directory, filename)
    file_exists = os.path.exists(file)
    logging.basicConfig(level=level,
                        format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.FileHandler(file), logging.StreamHandler()])
    return file_exists


def load_config(file: str) -> Config:
    """Load configuration from a YAML file.

    Args:
        file (str): The configuration file.

    Returns:
        Config: The loaded configuration.
    """
    try:
        with open(file, 'r') as f:
            return from_dict(data_class=Config, data=yaml.safe_load(f))
    except Exception as e:
        logging.error(f'Invalid configuration: {e}')


def str_response(response: requests.Response) -> str:
    """Create a string representation of a response object.

    Args:
        response (requests.Response): The response object to be represented as a string.

    Returns:
        str: A string representation of the response object.
    """
    return f'''{str(response.request.method)} {str(response.request.url)}
{str(response.request.headers)}
{str(response.request.body)}
{str(response.status_code)} {str(response.reason)}
{str(response.headers)}
{str(response.content)}'''


def get_entity_state(config: HomeAssistant) -> Optional[str]:
    """Get the state of an entity from Home Assistant.

    Args:
        config (HomeAssistant): The Home Assistant configuration.

    Returns:
        Optional[str]: The state of the entity, or None if the entity was not found or an error occurred.
    """
    url = f'{config.url}/api/states'
    headers = {'Authorization': f'Bearer {config.access_token}'}

    try:
        response = requests.get(url, headers=headers, verify=config.insecure)
        logging.debug(str_response(response))
    except Exception as e:
        logging.error(f'Unexpected error: {e}')
        return None

    if response.status_code != 200:
        logging.error(f'Unexpected status code: {response.status_code}')
        return None

    content_type = response.headers.get('Content-Type', '')
    if 'application/json' not in content_type:
        logging.error(f'Unexpected Content-Type: {content_type}')
        return None

    entity = next((e for e in response.json() if config.entity_id == e.get('entity_id', '')), None)
    if entity is None:
        logging.warning(f'Entity {config.entity_id} was not found')
        return None

    logging.debug(entity)
    return entity.get('state')


def post_slack_api(url: str, json: Any) -> bool:
    """Send a POST request to the Slack API and return True if the request was successful.

    Args:
        url (str): The URL of the Slack API endpoint.
        json (Any): The JSON payload to send in the request body.

    Returns:
        bool: True if the request was successful, False otherwise.
    """
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(url, headers=headers, json=json)
        logging.debug(str_response(response))
    except Exception as e:
        logging.error(f'Unexpected error: {e}')
        return False

    if response.status_code != 200:
        logging.error(f'Unexpected status code: {response.status_code}')
        return False

    content_type = response.headers.get('Content-Type', '')
    if 'application/json' not in content_type:
        logging.error(f'Unexpected Content-Type: {content_type}')
        return False

    return response.json().get('ok', False)


def post_slack_channel_message(config: SlackChannel) -> bool:
    """Posts a message to a Slack channel using the provided configuration.

    Args:
        config (SlackChannel): The Slack channel configuration object.

    Returns:
        bool: True if the message was posted successfully, False otherwise.
    """
    return post_slack_api(config.url, {'channel_id': config.channel, 'message': config.message})


def post_slack_user_message(config: SlackUser, message: str) -> bool:
    """Posts a message to a Slack user using the provided configuration.

    Args:
        config (SlackUser): The Slack user configuration object.
        message (str): The message to send to the Slack user.

    Returns:
        bool: True if the message was successfully posted, False otherwise.
    """
    return post_slack_api(config.url, {'user_id': config.user_id, 'message': message})


def main():
    """Main function to post office presence to a Slack channel.
    """
    # parse command line arguments
    args = parse_args()
    config_file = args.config
    entity_state = args.state
    log_level = args.log

    # initialize the logger and halt if already executed today
    if init_logger('log', f'{datetime.datetime.now().strftime("%Y-%m-%d")}.log', level=log_level):
        logging.info('Log file already exists. Skipping re-execution')
        return

    # load configuration - errors logged by function
    config = load_config(config_file)
    if config is None:
        return

    # fetch entity state if override not provided
    if entity_state is None:
        entity_state = get_entity_state(config.home_assistant)

    # retrieve Slack channel configuration based on entity state
    slack_channel = config.slack_channel(entity_state)

    # post message to Slack channel
    success = post_slack_channel_message(slack_channel)

    # determine summary message and post to the Slack user
    if success:
        summary = f"Successfully posted '{slack_channel.message}' to {slack_channel.channel}"
        logging.info(summary)
    else:
        summary = f"Failed to post '{slack_channel.message}' to {slack_channel.channel}"
        logging.error(summary)
    post_slack_user_message(config.slack_user, summary)


if __name__ == "__main__":
    main()
