import pytest
import time
import importlib
import sys
from pathlib import Path
import fixgw.quorum as quorum
import fixgw.database as fixdatabase

# Use this fixture in any test that needs fixgw.database
# It will provide a frshly init database for each test
@pytest.fixture
def database():
    importlib.reload(fixdatabase)
    importlib.reload(quorum) # as quorum
    # Set Quorum so it is usable if a test wants to
    # test quorum related features
    quorum.nodeid = 1
    quorum.vote_key = f"QVOTE{quorum.nodeid}"

    fixdatabase.init("src/fixgw/config/database.yaml")
    # Ensure the DB is fully loaded to avoid random 
    # dictionary changed size during iteration
    # errors
    loaded = False
    while not loaded:
        try:
            fixdatabase.get_raw_item("ZZLOADER")
            loaded = True
        except:
            time.sleep(0.01)
    return fixdatabase
    
