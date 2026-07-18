#!/usr/bin/env python3

"""Docker-compose-style subcommand example - see README "Subcommands / Command Tree".

Exercises the Command tree / decided_for / Terminal dispatch mechanics with a
real, runnable CLI instead of just an inline README snippet.
"""

import sys

import rudesheim.command_line as cl


class Up(cl.Command):
    @classmethod
    def run_with(this, run_parameters):
        print(f"up {list(run_parameters.arguments)}")


class Down(cl.Command):
    @classmethod
    def run_with(this, run_parameters):
        print(f"down {list(run_parameters.arguments)}")


class ComposeSubcommand(cl.SelectableCategory):
    @classmethod
    def selectables_defines(this):
        return [Up.tie(("up",), "start containers"), Down.tie(("down",), "stop containers")]

    @classmethod
    def default(this):
        # No subcommand typed here -> defer to Compose's own run_with(),
        # not Up's.
        return cl.Terminal


class Compose(cl.Command):
    @classmethod
    def parser_define(this):
        return cl.Parser([ComposeSubcommand])

    @classmethod
    def run_with(this, run_parameters):
        print("usage: compose [up|down]")


class RootSubcommand(cl.SelectableCategory):
    @classmethod
    def selectables_defines(this):
        return [Compose.tie(("compose",), "manage compose stacks")]

    @classmethod
    def default(this):
        # No token typed at all -> a real Command, not Terminal. There is no
        # enclosing Command here for Terminal to defer to.
        return Compose


def main():
    cl.Parser([RootSubcommand]).parse(sys.argv[1:])


if __name__ == "__main__":
    main()
