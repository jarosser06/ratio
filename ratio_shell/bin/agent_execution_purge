#!/bin/bash

# Capture the output of rto ls
directories=$(rto ls | grep "agent_exec-" | grep "/" | sed 's/\/$//')

# Loop through each directory and delete it
for dir in $directories; do
  echo "Deleting $dir"
  rto rm -rf "$dir"
done

echo "All agent_exec directories have been removed."
