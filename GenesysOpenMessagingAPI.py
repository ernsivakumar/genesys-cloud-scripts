import requests
import json
import logging
from datetime import datetime
import uuid
import time
from typing import Dict, Optional

# Configuration
CONFIG = {
    "client_id": "4e6b408f-1800-4232-bbf0-d61875ca3d61",
    "client_secret": "qLsuti3t35oYBnKYMfLcvQVIVtkKfa9vaHc-x1uFyaM",
    "region": "mec1",  # e.g., "us-east-1", "eu-west-1", etc.
    "deployment_id": "8fb78ca2-ea94-452f-9e80-7f5c18880629",  # Web Deployment ID
    "queue_id": "1f1c4346-b637-4280-8824-9d19b7b20ef4",  # Target queue ID
    "recipient": {
        "name": "Siva",
        "email": "er.nsivakumar@gmail.com",
        "phone": "+97142022180"  # Optional
    },
    "message": "Hello, I'd like to inquire about your services"
}

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"open_messaging_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("GenesysOpenMessaging")


class OpenMessagingClient:
    """Client for Genesys Cloud Open Messaging API"""

    def __init__(self):
        self.access_token = None
        self.auth_url = self._get_auth_url()
        self.api_base_url = self._get_api_base_url()
        self.session = requests.Session()

    def _get_auth_url(self) -> str:
        """Get the appropriate auth URL based on region"""
        region = CONFIG["region"]
        if region == "us-east-1":
            return "https://login.mypurecloud.com/oauth/token"
        return f"https://login.{region}.pure.cloud/oauth/token"

    def _get_api_base_url(self) -> str:
        """Get the appropriate API base URL based on region"""
        region = CONFIG["region"]
        if region == "us-east-1":
            return "https://api.mypurecloud.com"
        return f"https://api.{region}.pure.cloud"

    def authenticate(self) -> bool:
        """Authenticate with OAuth and get access token"""
        try:
            response = self.session.post(
                self.auth_url,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json"
                },
                auth=(CONFIG["client_id"], CONFIG["client_secret"]),
                data={"grant_type": "client_credentials"}
            )
            response.raise_for_status()

            self.access_token = response.json()["access_token"]
            logger.info("Successfully authenticated with Genesys Cloud")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication failed: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response content: {e.response.text}")
            return False

    def _make_api_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """Make an API request with proper headers"""
        if not self.access_token and not self.authenticate():
            return None

        url = f"{self.api_base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        try:
            response = self.session.request(
                method,
                url,
                headers=headers,
                json=data
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response content: {e.response.text}")
            return None

    def initiate_chat(self) -> Optional[Dict]:
        """Initiate a new Open Messaging chat conversation"""
        # Generate unique IDs for the conversation and participant
        conversation_id = str(uuid.uuid4())
        participant_id = str(uuid.uuid4())

        # Create the conversation structure
        conversation_data = {
            "id": conversation_id,
            "deploymentId": CONFIG["deployment_id"],
            "messengerType": "open",
            "participants": [
                {
                    "id": participant_id,
                    "type": "external",
                    "connectedTime": datetime.utcnow().isoformat() + "Z",
                    "name": CONFIG["recipient"]["name"],
                    "addresses": {
                        "email": CONFIG["recipient"]["email"]
                    },
                    "attributes": {
                        "role": "customer"
                    }
                }
            ],
            "direction": "outbound",
            "state": "alerting",
            "routing": {
                "targets": [
                    {
                        "type": "queue",
                        "id": CONFIG["queue_id"]
                    }
                ]
            }
        }

        # Add phone if provided
        if CONFIG["recipient"].get("phone"):
            conversation_data["participants"][0]["addresses"]["phone"] = CONFIG["recipient"]["phone"]

        logger.info(f"Initiating conversation with ID: {conversation_id}")

        # Create the conversation
        conversation = self._make_api_request(
            "POST",
            "/api/v2/conversations/messages/open",
            conversation_data
        )

        if not conversation:
            logger.error("Failed to create conversation")
            return None

        logger.info("Successfully created conversation")

        # Send the initial message
        message_data = {
            "body": {
                "contentType": "text/plain",
                "text": CONFIG["message"]
            },
            "senderId": participant_id,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        message = self._make_api_request(
            "POST",
            f"/api/v2/conversations/messages/{conversation_id}/messages",
            message_data
        )

        if not message:
            logger.error("Failed to send initial message")
            return None

        logger.info("Successfully sent initial message")

        return {
            "conversation_id": conversation_id,
            "participant_id": participant_id,
            "conversation": conversation,
            "message": message
        }


def main():
    logger.info("Starting Genesys Cloud Open Messaging client")

    client = OpenMessagingClient()

    # Authenticate
    if not client.authenticate():
        logger.error("Failed to authenticate. Exiting.")
        return

    # Initiate chat
    result = client.initiate_chat()

    if result:
        logger.info("Chat initiated successfully")
        logger.info(f"Conversation ID: {result['conversation_id']}")
        logger.info(f"Participant ID: {result['participant_id']}")
    else:
        logger.error("Failed to initiate chat")


if __name__ == "__main__":
    main()