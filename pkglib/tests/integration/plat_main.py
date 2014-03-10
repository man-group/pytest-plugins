# NOTE! We can only reliably import system modules or pkglib
# because other modules might not be available in the temporary
# virtualenvs that are created.
import sys
import functools

from pkglib.scripts import plat


def test_main(argv=sys.argv[1:]):
    """Entry point from integration tests.

    Mocks out colored output and prompting to facilitate testing.
    """
    plat.statusmsg = functools.partial(plat.cprint, file=sys.stdout)
    plat.errormsg = functools.partial(plat.cprint, file=sys.stderr)
    plat.warnmsg = functools.partial(plat.cprint, file=sys.stdout)

    yes_on_prompt = "--yes-on-prompt" in argv

    sys.argv = [arg for arg in argv if arg != "--yes-on-prompt"]

    def test_prompt(text):
        print(text)
        print("Answer: " + "Y" if yes_on_prompt else "N")
        return yes_on_prompt

    plat.prompt = test_prompt

    return plat.main(sys.argv)
