#!/usr/bin/env python3

"""Minimal smoke check for installed command-line-rudesheim-python."""

import rudesheim.command_line as cl


class DryRun(cl.Option):
    @classmethod
    def label(this):
        return "dry-run"


class Apply(cl.Option):
    @classmethod
    def label(this):
        return "apply"


class Mode(cl.SelectableCategory):
    @classmethod
    def selectables_defines(this):
        return [
            DryRun.tie(("d", "dry-run"), "do not mutate"),
            Apply.tie(("a", "apply"), "apply changes"),
        ]

    @classmethod
    def default(this):
        return DryRun


class Main(cl.Option):
    @classmethod
    def run_with(this, run_parameters):
        mode = run_parameters.categories[Mode]
        print(f"mode={mode.label()} args={run_parameters.arguments}")


class Running(cl.SelectableCategory):
    @classmethod
    def selectables_defines(this):
        return []

    @classmethod
    def default(this):
        return Main


def main():
    state = cl.Parser([Running, Mode]).resolve(["--apply", "target"])
    state.run_parameters.categories[Running].run_with(state.run_parameters)


if __name__ == "__main__":
    main()
