import requests
import json
from typing import List, Dict


class GenesysCloudClient:
    def __init__(self, client_id: str, client_secret: str, environment: str = "mypurecloud.com"):
        """
        Initialize Genesys Cloud client

        Args:
            client_id: OAuth client ID
            client_secret: OAuth client secret
            environment: Genesys Cloud environment (default: mypurecloud.com)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.environment = environment
        self.base_url = f"https://api.{environment}"
        self.access_token = None

    def authenticate(self) -> bool:
        """Authenticate and obtain access token"""
        auth_url = f"https://login.{self.environment}/oauth/token"

        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = {
            "grant_type": "client_credentials"
        }

        try:
            response = requests.post(
                auth_url,
                headers=headers,
                data=data,
                auth=(self.client_id, self.client_secret)
            )
            response.raise_for_status()

            token_data = response.json()
            self.access_token = token_data.get("access_token")
            print("✓ Authentication successful")
            return True

        except requests.exceptions.RequestException as e:
            print(f"✗ Authentication failed: {e}")
            return False

    def update_user_language_skills(self, user_id: str, language_skills: List[Dict]) -> bool:
        """
        Update language skills for a single user

        Args:
            user_id: User ID to update
            language_skills: List of language skill objects with id and proficiency

        Returns:
            True if successful, False otherwise
        """
        if not self.access_token:
            print("✗ Not authenticated. Please call authenticate() first.")
            return False

        url = f"{self.base_url}/api/v2/users/{user_id}/routinglanguages/bulk"

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.patch(url, headers=headers, json=language_skills)
            response.raise_for_status()
            print(f"✓ Successfully updated language skills for user: {user_id}")
            return True

        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to update user {user_id}: {e}")
            if hasattr(e.response, 'text'):
                print(f"  Response: {e.response.text}")
            return False

    def bulk_update_users_language_skills(
            self,
            user_ids: List[str],
            language_skills: List[Dict]
    ) -> Dict[str, bool]:
        """
        Update language skills for multiple users

        Args:
            user_ids: List of user IDs to update
            language_skills: List of language skill objects

        Returns:
            Dictionary mapping user IDs to success status
        """
        results = {}

        print(f"\nUpdating language skills for {len(user_ids)} users...")
        print("-" * 60)

        for user_id in user_ids:
            results[user_id] = self.update_user_language_skills(user_id, language_skills)

        print("-" * 60)
        successful = sum(1 for v in results.values() if v)
        print(f"\nCompleted: {successful}/{len(user_ids)} users updated successfully")

        return results


def main():
    # Configuration
    CLIENT_ID = "f5058337-3c19-4e97-8083-1ece156ddf63"
    CLIENT_SECRET = "ea07g551WJj1WDnZDj1p7HaB0gf9DGL4AHtGzQ2BSvg"
    ENVIRONMENT = "mec1.pure.cloud"  # Change based on your region

    # User IDs to update (comma-separated)
    USER_IDS = [
        "fbee8aeb-8842-441a-a184-e938231bba72",
        "824e638b-2131-404e-a1c6-3d78c0e2ae26",
        "72922a58-eeef-41cf-a29f-0d05f9036c83",
        "335fce29-8be5-41c7-886c-ee01f53c9b68",
        "4b9d28c0-47b7-47fd-9276-10f45fe317fc",
        "ef1210a0-0067-4dc6-a676-f17cfe63edec",
        "a87121b0-55c5-43a1-847f-44eeab12cbdc",
        "b3ce78a6-a23e-4f18-8d30-5a33aaa915ee",
        "640c0d6d-d25e-40fd-9076-2673c905b051",
        "28cd5261-e83b-4bf3-8839-f0cad2637a20",
        "ddb6955e-ac30-4ce2-94b9-22b00dc8eea6",
        "0814bf0d-71b6-41c2-b77e-870325faf21b",
        "5d84d215-5ae7-45bc-a823-638c9eab8105",
        "f9fc2cea-603d-4093-b32d-e80f601c762c",
        "bed31862-e587-4a8e-b62d-ab2da4c49a18",
        "fe23ab1a-036a-40a6-8608-2881770f5d6b",
        "cc4df434-2e6d-4a5c-a751-1c98db4d45a8",
        "3220102d-f40f-4cae-8141-c8bd4c6aa488",
        "f5755184-74a3-4c66-b953-465dc2853c65",
        "e1310a9e-38a8-4bbc-881b-9e45c3d1bb9d",
        "de184284-f561-408b-b54e-3694c93c42c8",
        "e1b0335c-9ce4-4744-8059-a6ba94dd3b09",
        "b87417d2-8c70-4261-b67e-ed8ccf58ff46",
        "58b624fd-0b21-49d5-bd3a-732bb4f089e8",
        "a945c1a9-c10c-4628-9cf7-7bec7163093b",
        "e95418fb-ad99-4a77-84bc-f13a5c6e5fc9",
        "4be35706-f193-4509-bdbd-b30a4c1ceeba",
        "337eb53a-4142-42f1-aabb-e4dc95e296af",
        "94bcbf28-20c6-461f-bc58-826484881bee",
        "74ee4bff-b0d1-4ef1-afac-becee291ba38",
        "551593a6-1991-4038-be94-9d9a1b845694",
        "9afe0e1f-139e-4161-b1bf-513c2266afa4",
        "5834d963-c92f-4ce5-81da-a9501bda2275",
        "5b5a75de-c135-4791-bb44-103e894e2501",
        "24ecb7e9-23a0-480f-8e7d-3f2ceaa9299a",
        "2ae52e9c-6be0-4e09-bf30-ea6ac4bd02be",
        "8cee8039-7c63-489b-9994-aa6a70ef3206",
        "7de817c5-7dc4-44cb-a853-3a6a1c6acfed",
        "8e33a93e-a265-4366-b3cc-854cc326444a",
        "1f8ad2e3-3ff3-4c8c-8574-744663f1a227",
        "43b4cd92-da7a-419e-a1dd-1c9e9d36cada",
        "5311cde2-1428-452e-926a-55504fa40506",
        "a3d65b31-a2ed-4323-abbf-438b364fa53b",
        "d33d9987-8668-47a9-adc9-194377d6f8ac",
        "fe49c49d-6ef0-4a45-ad91-f184a39027cd",
        "a4fc0e02-4e97-47d0-9b1a-349c2e4e8ad1",
        "afa5442f-e165-4d96-a3bf-4190cac2cbf8",
        "fc8a51c2-2512-4894-adc8-bbdaf2aace2e",
        "1b245c26-b85b-43d3-96b0-32b9307abe2a",
        "ad1b420f-6455-41ca-a825-a8ce8574bfac",
        "551b7fca-b66b-4cee-8315-da54c05ceb5f",
        "160b9bf6-62b8-4d46-acc2-0dad16b3e5b9",
        "1510cd8b-7ce3-4246-8cd9-3a74ff950f93",
        "a6bc768b-8365-4d0a-b637-fd8932dd6035"
    ]

    # Language skills to assign with proficiency levels
    # Proficiency: 0-5 (0=Not Rated, 1=Poor, 2=Fair, 3=Good, 4=Very Good, 5=Expert)
    LANGUAGE_SKILLS = [
        {
            "id": "50bffaae-c834-4ebe-b60b-1ad98f87652a",  # Replace with actual language skill ID
            "proficiency": 5
        },
        {
            "id": "87ffb12a-719a-479d-a2cf-55200070f18c",  # Replace with actual language skill ID
            "proficiency": 5
        }
    ]

    # Initialize client and authenticate
    client = GenesysCloudClient(CLIENT_ID, CLIENT_SECRET, ENVIRONMENT)

    if not client.authenticate():
        print("Failed to authenticate. Please check your credentials.")
        return

    # Update language skills for all users
    results = client.bulk_update_users_language_skills(USER_IDS, LANGUAGE_SKILLS)

    # Display results
    print("\n" + "=" * 60)
    print("FINAL RESULTS:")
    print("=" * 60)
    for user_id, success in results.items():
        status = "SUCCESS" if success else "FAILED"
        print(f"{user_id}: {status}")


if __name__ == "__main__":
    main()