from datetime import datetime, timedelta

# Layout settings
TITLE = "test dashboard"
LANGUAGE = "dutch"

# FEWS Settings
FEWS_URL = r"https://www.hydrobase.nl/fews/nzv/FewsWebServices/rest/fewspiservice/v1"
ROOT_FILTER = "WDB"
SSL_VERIFY = False

# Search Settings
FIRST_DATE = datetime(2010, 1, 1)
INIT_TIMEDELTA = timedelta(days=30)
