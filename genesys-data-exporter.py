import requests
import pandas as pd
from datetime import datetime
import json
import os
import logging
from logging.handlers import RotatingFileHandler
import sys
from typing import List, Dict, Optional, Union

# Configuration
CONFIG = {
    "client_id": "169d2073-9662-46b3-b429-e593fc99c419",
    "client_secret": "84y0sQ-CjWuDF-Gf1dUidmfaVlePz65JEbB2YIIjKTo",
    "region": "mec1",  # e.g., "us-east-1", "eu-west-1", etc.
    "output": {
        "directory": "exports",
        "users_filename": "genesys_users",
        "queues_filename": "genesys_queues",
        "skills_filename": "genesys_skills",
        "format": "csv",  # "csv" or "excel"
        "timestamp_format": "%Y%m%d_%H%M%S"
    },
    "logging": {
        "directory": "logs",
        "filename": "genesys_export",
        "max_bytes": 5 * 1024 * 1024,  # 5MB
        "backup_count": 3,
        "level": "DEBUG"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    },
    "api": {
        "page_size": 100,
        "max_retries": 3,
        "retry_delay": 2  # seconds
    }
}


# Set up logging
def setup_logging() -> logging.Logger:
    """Configure comprehensive logging system"""
    log_dir = CONFIG["logging"]["directory"]
    os.makedirs(log_dir, exist_ok=True)

    log_filename = f"{log_dir}/{CONFIG['logging']['filename']}_{datetime.now().strftime('%Y%m%d')}.log"

    logger = logging.getLogger("genesys_export")
    logger.setLevel(CONFIG["logging"]["level"].upper())

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_filename,
        maxBytes=CONFIG["logging"]["max_bytes"],
        backupCount=CONFIG["logging"]["backup_count"],
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(CONFIG["logging"]["level"].upper())

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


logger = setup_logging()


class GenesysAPI:
    """Genesys Cloud API client with retry logic"""

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
                    # Token might be expired, try to reauthenticate
                    if self._authenticate():
                        continue
                logger.error(f"HTTP error occurred: {http_err}")
                logger.error(f"Response content: {response.text}")
                break

            except Exception as e:
                logger.error(f"API request failed: {str(e)}", exc_info=True)
                if attempt < CONFIG["api"]["max_retries"] - 1:
                    logger.info(f"Retrying... Attempt {attempt + 2}")
                    time.sleep(CONFIG["api"]["retry_delay"])
                    continue

        return None

    def get_all_resources(self, resource_type: str) -> List[Dict]:
        """Get all resources of a specific type with pagination"""
        resources = []
        page_number = 1
        total_resources = 0

        try:
            logger.info(f"Starting {resource_type} data retrieval")

            while True:
                params = {
                    "pageSize": CONFIG["api"]["page_size"],
                    "pageNumber": page_number
                }

                if resource_type == "users":
                    params["expand"] = "presence,routingStatus,geolocation,authorization"

                logger.debug(f"Fetching {resource_type} page {page_number}")

                data = self._make_api_request(resource_type, params)
                if not data:
                    break

                current_resources = data.get("entities", [])
                resources_count = len(current_resources)
                total_resources += resources_count
                resources.extend(current_resources)

                logger.debug(f"Retrieved {resources_count} {resource_type} from page {page_number}")

                if resources_count < CONFIG["api"]["page_size"]:
                    logger.info(f"Completed {resource_type} retrieval. Total {resource_type}: {total_resources}")
                    break

                page_number += 1

        except Exception as e:
            logger.error(f"Error fetching {resource_type}: {str(e)}", exc_info=True)

        return resources


class DataProcessor:
    """Process and export Genesys Cloud data"""

    @staticmethod
    def flatten_dict(d: Dict, parent_key: str = '', sep: str = '_') -> Dict:
        """Flatten a nested dictionary structure"""
        items = {}
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.update(DataProcessor.flatten_dict(v, new_key, sep))
            elif isinstance(v, list):
                for i, item in enumerate(v):
                    if isinstance(item, dict):
                        items.update(DataProcessor.flatten_dict(item, f"{new_key}_{i}", sep))
                    else:
                        items[f"{new_key}_{i}"] = item
            else:
                items[new_key] = v
        return items

    @staticmethod
    def process_users(users: List[Dict]) -> List[Dict]:
        """Process user data with selected columns: id, name, division_name, email"""
        processed_users = []

        try:
            logger.info("Starting user data processing")

            for user in users:
                try:
                    # Extract only required fields
                    division = user.get('division', {})
                    processed_user = {
                        'id': user.get('id'),
                        'name': user.get('name'),
                        'division_name': division.get('name') if isinstance(division, dict) else None,
                        'email': user.get('email')
                    }
                    processed_users.append(processed_user)

                except Exception as e:
                    logger.warning(f"Error processing user {user.get('id')}: {str(e)}")
                    continue

            logger.info(f"Completed processing {len(processed_users)} users")

        except Exception as e:
            logger.error(f"Error in process_users: {str(e)}", exc_info=True)

        return processed_users

    @staticmethod
    def process_queues(queues: List[Dict]) -> List[Dict]:
        """Process queue data with all available properties"""
        processed_queues = []

        try:
            logger.info("Starting queue data processing")

            for queue in queues:
                try:
                    # Flatten the entire queue object
                    flat_queue = DataProcessor.flatten_dict(queue)
                    processed_queues.append(flat_queue)

                except Exception as e:
                    logger.warning(f"Error processing queue {queue.get('id')}: {str(e)}")
                    continue

            logger.info(f"Completed processing {len(processed_queues)} queues")

        except Exception as e:
            logger.error(f"Error in process_queues: {str(e)}", exc_info=True)

        return processed_queues

    @staticmethod
    def process_skills(skills: List[Dict]) -> List[Dict]:
        """Process skill data with all available properties"""
        processed_skills = []

        try:
            logger.info("Starting skill data processing")

            for skill in skills:
                try:
                    # Flatten the entire skill object
                    flat_skill = DataProcessor.flatten_dict(skill)
                    processed_skills.append(flat_skill)

                except Exception as e:
                    logger.warning(f"Error processing skill {skill.get('id')}: {str(e)}")
                    continue

            logger.info(f"Completed processing {len(processed_skills)} skills")

        except Exception as e:
            logger.error(f"Error in process_skills: {str(e)}", exc_info=True)

        return processed_skills

    @staticmethod
    def export_data(data: List[Dict], resource_type: str) -> bool:
        """Export data to file based on configuration"""
        try:
            os.makedirs(CONFIG["output"]["directory"], exist_ok=True)

            filename = {
                "users": CONFIG["output"]["users_filename"],
                "queues": CONFIG["output"]["queues_filename"],
                "skills": CONFIG["output"]["skills_filename"]
            }.get(resource_type, "export")

            timestamp = datetime.now().strftime(CONFIG["output"]["timestamp_format"])
            file_path = f"{CONFIG['output']['directory']}/{filename}_{timestamp}"

            df = pd.DataFrame(data)

            if CONFIG["output"]["format"].lower() == "csv":
                file_path += ".csv"
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
            else:
                file_path += ".xlsx"
                df.to_excel(file_path, index=False)

            logger.info(f"Successfully exported {len(data)} {resource_type} to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error exporting {resource_type} data: {str(e)}", exc_info=True)
            return False


def main():
    try:
        logger.info("=" * 80)
        logger.info("Genesys Cloud Data Export Script Started")
        logger.info(f"Start Time: {datetime.now()}")
        logger.info(f"Configuration: {json.dumps(CONFIG, indent=2)}")

        api = GenesysAPI()

        # Export Users
        logger.info("-" * 80)
        logger.info("Starting User Export")
        users = api.get_all_resources("users")
        if users:
            processed_users = DataProcessor.process_users(users)
            DataProcessor.export_data(processed_users, "users")

        # Export Queues
        logger.info("-" * 80)
        logger.info("Starting Queue Export")
        queues = api.get_all_resources("routing/queues")
        if queues:
            processed_queues = DataProcessor.process_queues(queues)
            DataProcessor.export_data(processed_queues, "queues")

        # Export Skills
        logger.info("-" * 80)
        logger.info("Starting Skill Export")
        skills = api.get_all_resources("routing/skills")
        if skills:
            processed_skills = DataProcessor.process_skills(skills)
            DataProcessor.export_data(processed_skills, "skills")

        logger.info("-" * 80)
        logger.info("Script Completed Successfully")
        logger.info(f"End Time: {datetime.now()}")
        logger.info("=" * 80)

    except Exception as e:
        logger.critical(f"Script failed: {str(e)}", exc_info=True)
        logger.info("=" * 80)


if __name__ == "__main__":
    import time  # Import moved here to avoid shadowing time.sleep in methods

    main()