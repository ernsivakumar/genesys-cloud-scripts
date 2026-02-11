# Genesys Cloud User Export

Export Genesys Cloud users with their assigned divisions, skills, and queues.

## Output Fields
- User Name
- Email Address  
- Division
- Assigned Skills
- Assigned Queues

## Setup

1. Update the CONFIG section with your credentials:
```python
CONFIG = {
    "client_id": "your-client-id",
    "client_secret": "your-client-secret",
    "region": "your-region"
}
```

2. Install dependencies:
```bash
pip install requests pandas
```

3. Run the script:
```bash
python genesys-users-export-with-skills-queues.py
```

## Output
Results are saved to `exports/` directory as CSV or Excel file.
