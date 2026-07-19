#!/usr/bin/env zsh

# Drops you into an interactive zsh with Tab-completion for deploy.py already
# wired up - no need to touch your real ~/.zshrc just to try it. Run this
# script directly:
#
#   ./deploy-completion-shell.zsh
#
# then, inside the shell it puts you in, just type `./deploy.py <Tab>` /
# `./deploy.py service <Tab>` / etc. Exit that shell (Ctrl+D or `exit`) to
# return to whatever shell you launched this from - nothing here persists
# afterwards.
#
# How: rather than editing your real ~/.zshrc, this points ZDOTDIR at a
# throwaway directory holding a minimal generated .zshrc that exports
# PYTHONPATH so `import rudesheim.command_line` in deploy.py resolves
# without a separate `export PYTHONPATH=../lib` step, runs compinit, defines
# the `_deploy_py` completion function (see the "Tab Completion" section of
# README.md for what it does and why it's built this way - the
# $CURRENT-based reconstruction of the word under the cursor in particular),
# and registers it via `compdef`. The temp directory is removed again once
# you exit the shell.

here="${0:A:h}"
libdir="${here:h}/lib"
zdotdir="$( mktemp -d )"
trap 'rm -rf "$zdotdir"' EXIT

cat > "$zdotdir/.zshrc" <<'RC'
autoload -Uz compinit && compinit

_deploy_py()
{
	local -a candidates already_typed
	already_typed=( ${words[2,CURRENT-1]} )
	candidates=( ${(f)"$( ${words[1]} --complete ${already_typed} "${words[CURRENT]}" )"} )
	compadd -a candidates
}
compdef _deploy_py deploy.py
RC

print -r -- "export PYTHONPATH=${(qq)libdir}\${PYTHONPATH:+:\$PYTHONPATH}" >> "$zdotdir/.zshrc"
print -r -- "cd ${(qq)here}" >> "$zdotdir/.zshrc"
print -r -- "print 'Tab-completion for ./deploy.py is ready - try: ./deploy.py <Tab>'" >> "$zdotdir/.zshrc"

ZDOTDIR="$zdotdir" zsh -i
