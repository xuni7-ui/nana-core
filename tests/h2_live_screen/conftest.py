import pytest

def pytest_addoption(parser):parser.addoption('--live-screen',action='store_true',default=False,help='Explicitly enable owned dummy OS display qualification; never an ambient desktop')
@pytest.fixture
def live_screen(request):
    if not request.config.getoption('--live-screen'):pytest.skip('explicit --live-screen required')
