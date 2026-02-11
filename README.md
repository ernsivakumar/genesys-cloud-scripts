# Genesys Cloud Python Scripts

A collection of Python scripts for interacting with Genesys Cloud API.

## Scripts

### genesys-users-export-with-skills-queues.py
Exports user data with their assigned divisions, skills, and queues.

**Output Fields:**
- User Name
- Email Address
- Division
- Assigned Skills
- Assigned Queues

**Usage:**
```bash
python genesys-users-export-with-skills-queues.py
```

### genesys-data-exporter.py
General data exporter for users, queues, and skills.

## Configuration

Update the `CONFIG` dictionary in each script with your credentials:

```python
CONFIG = {
    "client_id": "your-client-id",
    "client_secret": "your-client-secret",
    "region": "mec1"  # Your Genesys region
}
```

## Requirements

- Python 3.7+
- requests
- pandas

Install dependencies:
```bash
pip install requests pandas
```

## Security Notes

- Never commit credentials to version control
- Use environment variables for sensitive data in production
- Export files and logs are excluded from git via .gitignore

## License

MIT License
