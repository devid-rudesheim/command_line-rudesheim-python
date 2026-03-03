#!/usr/bin/env python3

"""Minimal smoke check for installed command-line-rudesheim-python."""

import rudesheim.command_line as cl


class DryRun(cl.Option):
    @classmethod
    def label(cls):
        return "dry-run"


class Apply(cl.Option):
    @classmethod
    def label(cls):
        return "apply"


class Mode(cl.OptionCategory):
    @classmethod
    def options_defines(cls):
        return [
            DryRun.tie(("d", "dry-run"), "do not mutate"),
            Apply.tie(("a", "apply"), "apply changes"),
        ]

    @classmethod
    def default(cls):
        return DryRun


class Main(cl.OptionForRun):
    @classmethod
    def run_with(cls, categories, arguments):
        mode = categories[Mode]
        print(f"mode={mode.label()} args={arguments}")


class Running(cl.OptionCategory):
    @classmethod
    def options_defines(cls):
        return []

    @classmethod
    def default(cls):
        return Main


def main():
    categories, arguments = cl.Parser([Running, Mode]).parse(["--apply", "target"])
    categories[Running].run_with(categories, arguments)


if __name__ == "__main__":
    main()
