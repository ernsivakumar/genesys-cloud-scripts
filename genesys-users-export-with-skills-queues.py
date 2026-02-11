import requests
import pandas as pd
from datetime import datetime
import json
import os
import logging
from logging.handlers import RotatingFileHandler
import sys
from typing import List, Dict, Optional, Tuple
import time

# Configuration
CONFIG = {
    "client_id": "XXXX",
    "client_secret": "XXXX",
    "region": "mec1",  # e.g., "us-east-1", "eu-west-1", etc.
    "output": {
        "directory": "exports",
        "filename": "genesys_users_with_skills_queues",
        "format": "csv",  # "csv" or "excel"
        "timestamp_format": "%Y%m%d_%H%M%S"
    },
    "logging": {
        "directory": "logs",
        "filename": "genesys_user_export",
        "max_bytes": 5 * 1024 * 1024,  # 5MB
        "backup_count": 3,
        "level": "DEBUG"
    },
    "api": {
        "page_size": 100,
        "max_retries": 3,
        "retry_delay": 2
    }
}


def setup_logging() -> logging.Logger:
    """Configure comprehensive logging system"""
    log_dir = CONFIG["logging"]["directory"]
    os.makedirs(log_dir, exist_ok=True)

    log_filename = f"{log_dir}/{CONFIG['logging']['filename']}_{datetime.now().strftime('%Y%m%d')}.log"

    logger = logging.getLogger("genesys_user_export")
    logger.setLevel(CONFIG["logging"]["level"].upper())

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_handler = RotatingFileHandler(
        log_filename,
        maxBytes=CONFIG["logging"]["max_bytes"],
        backupCount=CONFIG["logging"]["backup_count"],
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(CONFIG["logging"]["level"].upper())

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


logger = setup_logging()


class GenesysAPI:
    """Genesys Cloud API client"""

    def __init__(self):
        self.access_token = None
        self.base_url = self._get_api_base_url()
        self.auth_url = self._get_auth_url()

    def _get_api_base_url(self) -> str:
        region = CONFIG["region"]
        if region == "us-east-1":
            return "https://api.mypurecloud.com/api/v2"
        return f"https://api.{region}.pure.cloud/api/v2"

    def _get_auth_url(self) -> str:
        region = CONFIG["region"]
        if region == "us-east-1":
            return "https://login.mypurecloud.com/oauth/token"
        return f"https://login.{region}.pure.cloud/oauth/token"

    def _authenticate(self) -> bool:
        """Authenticate and get OAuth token"""
        try:
            logger.info("Starting OAuth authentication")

            for attempt in range(CONFIG["api"]["max_retries"]):
                try:
                    response = requests.post(
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
                    if attempt < CONFIG["api"]["max_retries"] - 1:
                        logger.warning(f"Authentication attempt {attempt + 1} failed. Retrying...")
                        time.sleep(CONFIG["api"]["retry_delay"])
                        continue
                    raise

        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}", exc_info=True)
            return False

    def _make_api_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make API request with retry logic"""
        if not self.access_token and not self._authenticate():
            return None

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        url = f"{self.base_url}/{endpoint}"

        for attempt in range(CONFIG["api"]["max_retries"]):
            try:
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                return response.json()

            except requests.exceptions.HTTPError as http_err:
                if response.status_code == 401 and attempt == 0:
                    if self._authenticate():
                        continue
                logger.error(f"HTTP error occurred: {http_err}")
                logger.error(f"Response content: {response.text}")
                break

            except Exception as e:
                logger.error(f"API request failed: {str(e)}", exc_info=True)
                if attempt < CONFIG["api"]["max_retries"] - 1:
                    time.sleep(CONFIG["api"]["retry_delay"])
                    continue

        return None

    def get_all_users(self) -> List[Dict]:
        """Get all users with pagination"""
        users = []
        page_number = 1

        try:
            logger.info("Starting user data retrieval")

            while True:
                params = {
                    "pageSize": CONFIG["api"]["page_size"],
                    "pageNumber": page_number,
                    "expand": "division"
                }

                data = self._make_api_request("users", params)
                if not data:
                    break

                current_users = data.get("entities", [])
                users.extend(current_users)

                logger.info(f"Retrieved {len(current_users)} users from page {page_number}")

                if len(current_users) < CONFIG["api"]["page_size"]:
                    logger.info(f"Completed user retrieval. Total users: {len(users)}")
                    break

                page_number += 1

        except Exception as e:
            logger.error(f"Error fetching users: {str(e)}", exc_info=True)

        return users

    def get_user_skills(self, user_id: str) -> List[str]:
        """Get skills assigned to a user"""
        skills = []
        page_number = 1

        try:
            while True:
                params = {
                    "pageSize": CONFIG["api"]["page_size"],
                    "pageNumber": page_number
                }

                endpoint = f"users/{user_id}/routingskills"
                data = self._make_api_request(endpoint, params)

                if not data:
                    break

                entities = data.get("entities", [])
                for entity in entities:
                    skill_name = entity.get("name")
                    if skill_name:
                        skills.append(skill_name)

                if len(entities) < CONFIG["api"]["page_size"]:
                    break

                page_number += 1

        except Exception as e:
            logger.warning(f"Error fetching skills for user {user_id}: {str(e)}")

        return skills

    def get_user_queues(self, user_id: str) -> List[str]:
        """Get queues assigned to a user"""
        queues = []
        page_number = 1

        try:
            while True:
                params = {
                    "pageSize": CONFIG["api"]["page_size"],
                    "pageNumber": page_number
                }

                endpoint = f"users/{user_id}/queues"
                data = self._make_api_request(endpoint, params)

                if not data:
                    break

                entities = data.get("entities", [])
                for entity in entities:
                    queue_name = entity.get("name")
                    if queue_name:
                        queues.append(queue_name)

                if len(entities) < CONFIG["api"]["page_size"]:
                    break

                page_number += 1

        except Exception as e:
            logger.warning(f"Error fetching queues for user {user_id}: {str(e)}")

        return queues


class UserDataProcessor:
    """Process user data with skills and queues"""

    @staticmethod
    def process_user_data(users: List[Dict], api: GenesysAPI) -> List[Dict]:
        """Process user data with division, skills, and queues"""
        processed_users = []

        try:
            logger.info("Starting user data processing")
            total_users = len(users)

            for idx, user in enumerate(users, 1):
                try:
                    user_id = user.get('id')
                    user_name = user.get('name')

                    logger.info(f"Processing user {idx}/{total_users}: {user_name}")

                    # Get division
                    division = user.get('division', {})
                    division_name = division.get('name', '') if isinstance(division, dict) else ''

                    # Get email
                    email = user.get('email', '')

                    # Get skills
                    logger.debug(f"Fetching skills for user: {user_name}")
                    skills = api.get_user_skills(user_id)
                    skills_str = '; '.join(skills) if skills else ''

                    # Get queues
                    logger.debug(f"Fetching queues for user: {user_name}")
                    queues = api.get_user_queues(user_id)
                    queues_str = '; '.join(queues) if queues else ''

                    processed_user = {
                        'User Name': user_name,
                        'Email Address': email,
                        'Division': division_name,
                        'Assigned Skills': skills_str,
                        'Assigned Queues': queues_str
                    }

                    processed_users.append(processed_user)

                except Exception as e:
                    logger.warning(f"Error processing user {user.get('id')}: {str(e)}")
                    continue

            logger.info(f"Completed processing {len(processed_users)} users")

        except Exception as e:
            logger.error(f"Error in process_user_data: {str(e)}", exc_info=True)

        return processed_users

    @staticmethod
    def export_data(data: List[Dict]) -> bool:
        """Export data to CSV or Excel"""
        try:
            os.makedirs(CONFIG["output"]["directory"], exist_ok=True)

            timestamp = datetime.now().strftime(CONFIG["output"]["timestamp_format"])
            file_path = f"{CONFIG['output']['directory']}/{CONFIG['output']['filename']}_{timestamp}"

            df = pd.DataFrame(data)

            if CONFIG["output"]["format"].lower() == "csv":
                file_path += ".csv"
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
            else:
                file_path += ".xlsx"
                df.to_excel(file_path, index=False)

            logger.info(f"Successfully exported {len(data)} users to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error exporting data: {str(e)}", exc_info=True)
            return False


def main():
    try:
        logger.info("=" * 80)
        logger.info("Genesys Cloud Users Export with Skills and Queues - Script Started")
        logger.info(f"Start Time: {datetime.now()}")

        api = GenesysAPI()

        # Get all users
        logger.info("-" * 80)
        logger.info("Fetching all users")
        users = api.get_all_users()

        if users:
            # Process users with skills and queues
            logger.info("-" * 80)
            logger.info("Fetching skills and queues for each user")
            processed_users = UserDataProcessor.process_user_data(users, api)

            # Export data
            logger.info("-" * 80)
            logger.info("Exporting data")
            UserDataProcessor.export_data(processed_users)

        logger.info("-" * 80)
        logger.info("Script Completed Successfully")
        logger.info(f"End Time: {datetime.now()}")
        logger.info("=" * 80)

    except Exception as e:
        logger.critical(f"Script failed: {str(e)}", exc_info=True)
        logger.info("=" * 80)


if __name__ == "__main__":
    main()
