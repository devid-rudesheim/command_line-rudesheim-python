#!/usr/bin/env python3

"""Two-level Command tree example with multiple Options/Commands and
`-h`/`--help` at every level.

Demonstrates, all at once:
  - two nested Parser levels: the root level, and each of "service"/
    "config"'s own subcommand level
  - multiple Options *and* multiple Commands declared at every level
  - an in-between Command ("service"/"config") that is itself runnable
    without picking one of its own subcommands - via its subcommand
    category's default() returning cl.Terminal, same mechanism as
    compose.py's Compose/ComposeSubcommand
  - `-h`/`--help` (BasicHelp) available at every level, listing exactly
    that level's own Options/Commands
"""

import sys

import rudesheim.command_line as cl


class Verbose(cl.Option):
    pass


class Quiet(cl.Option):
    pass


class GlobalOptionCategory(cl.SelectableCategory):
    @classmethod
    def selectables_defines(this):
        return [
            Verbose.tie(("v", "verbose"), "verbose output"),
            Quiet.tie(("q", "quiet"), "suppress output"),
        ]

    @classmethod
    def default(this):
        return Quiet


class NoHelp(cl.Option):
    pass


class Root(cl.Command):
    @classmethod
    def run_with(this, run_parameters):
        help_selected = run_parameters.categories[RootHelpCategory]

        if isinstance(help_selected, RootHelp):
            return help_selected.run_with(run_parameters)

        print("usage: deploy.py [-v|-q] <service|config> ...")


# --- service subtree -----------------------------------------------------

class Detach(cl.Option):
    pass


class Foreground(cl.Option):
    pass


class ServiceOptionCategory(cl.SelectableCategory):
    @classmethod
    def selectables_defines(this):
        return [
            Detach.tie(("d", "detach"), "run in the background"),
            Foreground.tie(("f", "foreground"), "run in the foreground"),
        ]

    @classmethod
    def default(this):
        return Foreground


class Start(cl.Command):
    @classmethod
    def run_with(this, run_parameters):
        print(f"service start {list(run_parameters.arguments)}")


class Stop(cl.Command):
    @classmethod
    def run_with(this, run_parameters):
        print(f"service stop {list(run_parameters.arguments)}")


class ServiceCommandCategory(cl.SelectableCategory):
    @classmethod
    def selectables_defines(this):
        return [Start.tie(("start",), "start the service"), Stop.tie(("stop",), "stop the service")]

    @classmethod
    def default(this):
        # No further subcommand typed -> defer to Service's own run_with(),
        # not Start's - this is what lets `deploy.py service` run on its own.
        return cl.Terminal


service_categories_templates = []


class ServiceHelp(cl.BasicHelp):
    @classmethod
    def usage(this):
        return ["deploy.py service [-d|-f] <start|stop> [args...]"]


class ServiceHelpCategory(cl.SelectableCategory):
    @classmethod
    def selectables_defines(this):
        global service_categories_templates

        return [cl.DefineOfOption(ServiceHelp(service_categories_templates), ("h", "help"), "show this help and exit")]

    @classmethod
    def default(this):
        return NoHelp


class Service(cl.Command):
    @classmethod
    def parser_define(this):
        return cl.Parser(service_categories_templates)

    @classmethod
    def run_with(this, run_parameters):
        help_selected = run_parameters.categories[ServiceHelpCategory]

        if isinstance(help_selected, ServiceHelp):
            return help_selected.run_with(run_parameters)

        print(f"service status ({run_parameters.categories[ServiceOptionCategory].__name__})")


service_categories_templates = [ServiceOptionCategory, ServiceHelpCategory, ServiceCommandCategory]


# --- config subtree -------------------------------------------------------

class Global(cl.Option):
    pass


class Local(cl.Option):
    pass


class ConfigOptionCategory(cl.SelectableCategory):
    @classmethod
    def selectables_defines(this):
        return [
            Global.tie(("g", "global"), "operate on the global config"),
            Local.tie(("l", "local"), "operate on the local config"),
        ]

    @classmethod
    def default(this):
        return Local


class Get(cl.Command):
    @classmethod
    def run_with(this, run_parameters):
        print(f"config get {list(run_parameters.arguments)}")


class Set(cl.Command):
    @classmethod
    def run_with(this, run_parameters):
        print(f"config set {list(run_parameters.arguments)}")


class ConfigCommandCategory(cl.SelectableCategory):
    @classmethod
    def selectables_defines(this):
        return [Get.tie(("get",), "read a config value"), Set.tie(("set",), "write a config value")]

    @classmethod
    def default(this):
        # Same Terminal fallback as ServiceCommandCategory - `deploy.py
        # config` alone runs Config's own run_with().
        return cl.Terminal


config_categories_templates = []


class ConfigHelp(cl.BasicHelp):
    @classmethod
    def usage(this):
        return ["deploy.py config [-g|-l] <get|set> [args...]"]


class ConfigHelpCategory(cl.SelectableCategory):
    @classmethod
    def selectables_defines(this):
        global config_categories_templates

        return [cl.DefineOfOption(ConfigHelp(config_categories_templates), ("h", "help"), "show this help and exit")]

    @classmethod
    def default(this):
        return NoHelp


class Config(cl.Command):
    @classmethod
    def parser_define(this):
        return cl.Parser(config_categories_templates)

    @classmethod
    def run_with(this, run_parameters):
        help_selected = run_parameters.categories[ConfigHelpCategory]

        if isinstance(help_selected, ConfigHelp):
            return help_selected.run_with(run_parameters)

        print(f"config status ({run_parameters.categories[ConfigOptionCategory].__name__})")


config_categories_templates = [ConfigOptionCategory, ConfigHelpCategory, ConfigCommandCategory]


# --- root level ------------------------------------------------------------

class RootCommandCategory(cl.SelectableCategory):
    @classmethod
    def selectables_defines(this):
        return [Service.tie(("service",), "manage the service"), Config.tie(("config",), "manage configuration")]

    @classmethod
    def default(this):
        # No token typed at all -> a real Command, not Terminal - there is
        # no enclosing Command here for Terminal to defer to.
        return Root


root_categories_templates = []


class RootHelp(cl.BasicHelp):
    @classmethod
    def usage(this):
        return ["deploy.py [-v|-q] <service|config> [options] [args...]"]


class RootHelpCategory(cl.SelectableCategory):
    @classmethod
    def selectables_defines(this):
        global root_categories_templates

        return [cl.DefineOfOption(RootHelp(root_categories_templates), ("h", "help"), "show this help and exit")]

    @classmethod
    def default(this):
        return NoHelp


root_categories_templates = [GlobalOptionCategory, RootHelpCategory, RootCommandCategory]


def main():
    parser = cl.Parser(root_categories_templates)

    # `--complete <words...>` prints one completion candidate per line for the
    # last word in <words...> instead of running the command - see
    # Parser.complete()'s docstring for the exact contract (last word = the
    # partial word being completed, "" if starting a fresh word).
    if 1 < len(sys.argv) and "--complete" == sys.argv[1]:
        for candidate in parser.complete(sys.argv[2:]):
            print(candidate)
        return

    parser.parse(sys.argv[1:])


if __name__ == "__main__":
    main()
