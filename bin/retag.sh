#!/bin/bash

for commit in $(git log --oneline -20 | grep -e "chapter[0-9][0-9]-start" | tr " " ","); do
  COMMIT_HASH=$(echo $commit | cut -d "," -f 1)
  TAG=$(echo $commit | cut -d "," -f 2)
  echo "=== === === $COMMIT_HASH $TAG === === ==="
  git tag -f $TAG $COMMIT_HASH
  git push -f origin $TAG
done