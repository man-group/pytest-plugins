"""  Repository fixtures
"""
import pytest
from pytest_shutil.workspace import Workspace
from git import Repo


@pytest.yield_fixture
def git_repo(request):
    """ Function-scoped fixture to create a new git repo in a temporary workspace.
    
        Attributes
        ----------
        uri (str) :  Repository URI
        api (`git.Repo`) :  Git Repo object for this repository
        .. also inherits all attributes from the `workspace` fixture
        
    """
    with GitRepo() as repo:
        yield repo


class GitRepo(Workspace):
    """
    Creates an empty Git repository in a temporary workspace.
    Cleans up on exit.

    Attributes
    ----------
    uri : `str`
        repository base uri
    api : `git.Repo` handle to the repository
    """
    def __init__(self):
        super(GitRepo, self).__init__()
        self.api = Repo.init(self.workspace)
        self.uri = "file://%s" % self.workspace
