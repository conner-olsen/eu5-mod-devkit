#!/usr/bin/env bash
set -e

rsync -av --inplace --no-times in_game main_menu release/

rm -rf ../mod-devkit
cp -r release ../mod-devkit

find release -mindepth 1 -maxdepth 1 ! -name '.metadata' -exec rm -rf {} +
