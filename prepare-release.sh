#!/usr/bin/env bash
set -e

rsync -av --inplace --no-times in_game main_menu dist/

rm -rf ../mod-devkit
cp -r dist ../mod-devkit

find dist -mindepth 1 -maxdepth 1 ! -name '.metadata' -exec rm -rf {} +
