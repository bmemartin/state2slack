import argparse
import dacite
import dataclasses
import datetime
import logging
import os
import requests
import typing
import yaml


@dataclasses.dataclass
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


@dataclasses.dataclass
class SlackState:
    """The configuration for Slack state message issuance.

    Attributes:
        webhook_url (str): The webhook URL for sending state messages.
        message (str): The message content.
        target_id (str, optional): The target ID of the message recipient. Defaults to None.
    """
    webhook_url: str
    message: str
    target_id: str = None


@dataclasses.dataclass
class SlackSummary:
    """The configuration for Slack summary message issuance.

    Attributes:
        webhook_url (str): The webhook URL for sending summary messages.
        target_id (str, optional): The target ID of the message recipient. Defaults to None.
    """
    webhook_url: str
    target_id: str = None


@dataclasses.dataclass
class Config:
    """The project configuration.

    Attributes:
        home_assistant (HomeAssistant): The Home Assistant configuration.
        slack_states (dict[str, Optional[SlackState]]): The Slack state configuration.
        slack_summary (SlackSummary, optional): The Slack summary configuration. Defaults to None.
    """
    home_assistant: HomeAssistant
    slack_states: dict[str, typing.Optional[SlackState]]
    slack_summary: SlackSummary = None

    def slack_state(self, value: str) -> SlackState:
        """Returns the SlackState object corresponding to the given value.
        If no SlackState object exists for the given value, the default SlackState object is returned.

        Args:
            value (str): The value to search for in the SlackState collection.

        Returns:
            SlackState: The SlackState object corresponding to the given value, or the default SlackState object if no match is found.
        """
        return self.slack_states.get(str(value).lower(), self.slack_states.get('default'))


def parse_args():
    """Parse command line strings into Python objects.

    Returns:
        args: the parsed command line arguments
    """
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-v', '--verbose', action='store_true', help='make the operation more talkative')
    parser.add_argument('--config',
                        type=str,
                        default='config.yaml',
                        help='path to configuration file (default: config.yaml)')
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
            return dacite.from_dict(data_class=Config, data=yaml.safe_load(f))
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


def get_entity_state(config: HomeAssistant) -> typing.Optional[str]:
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


def post_slack_webhook(url: str, json: typing.Any) -> bool:
    """Send a POST request to the Slack webhook URL and return True if the request was successful.

    Args:
        url (str): The URL of the Slack webhook.
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


def send_slack_state_message(config: SlackState) -> bool:
    """Sends a message to a Slack webhook using the provided configuration.

    Args:
        config (SlackState): The SlackState object.

    Returns:
        bool: True if the message was sent successfully, False otherwise.
    """
    payload = {'message': config.message}
    if config.target_id is not None:
        payload['target_id'] = config.target_id
    return post_slack_webhook(config.webhook_url, payload)


def send_slack_summary_message(config: SlackSummary, message: str) -> bool:
    """Sends a message to a Slack webhook using the provided configuration.

    Args:
        config (SlackSummary): The SlackSummary object.
        message (str): The message content.

    Returns:
        bool: True if the message was successfully sent, False otherwise.
    """
    payload = {'message': message}
    if config.target_id is not None:
        payload['target_id'] = config.target_id
    return post_slack_webhook(config.webhook_url, payload)


def build_summary_message(config: SlackState, success: bool) -> str:
    """Build a summary message based on the success of a Slack webhook request.

    Args:
        config (SlackState): The SlackState object.
        success (bool): True if the message was successfully sent.

    Returns:
        str: A summary message indicating the outcome of sending a Slack message.
    """
    if success:
        summary = f'Successfully sent "{config.message}"'
    else:
        summary = f'Failed to send "{config.message}"'
    if config.target_id is not None:
        summary += f' to {config.target_id}'
    return summary


def main():
    """Main function to send a curated message to Slack based on a Home Assistant entity's state.
    """
    # parse command line arguments
    args = parse_args()
    config_file = args.config
    entity_state = args.state
    log_level = 'DEBUG' if args.verbose else 'INFO'

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
        logging.info(f'Entity state identified as {entity_state}')
    else:
        logging.info(f'Entity state manually set to {entity_state}. Skipping entity discovery')

    # retrieve Slack state configuration based on entity state
    slack_state = config.slack_state(entity_state)

    # skip sending a Slack message entity state is undefined
    if slack_state is None:
        logging.warning('No Slack configuration found. Skipping message issuance')
        return

    # send state message to Slack
    success = send_slack_state_message(slack_state)

    # build and log summary message
    summary = build_summary_message(slack_state, success)
    logging.info(summary) if success else logging.warning(summary)

    # send summary message to Slack, if configured
    if config.slack_summary:
        send_slack_summary_message(config.slack_summary, summary)


if __name__ == "__main__":
    main()
