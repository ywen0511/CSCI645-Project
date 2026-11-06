#!/usr/bin/env bash
# Laptop-side: wait until every given LSF job ID is DONE or EXIT (max N minutes), print final states.
MAXMIN=${MAXMIN:-240}
for i in $(seq 1 $((MAXMIN * 2))); do
  s=$(${LSF_SSH:-bash -c} "bjobs -a -w $* 2>&1" 2>/dev/null | grep -v -E "mux|ControlSocket")
  n=$(echo "$s" | grep -cE " (DONE|EXIT) ")
  [ "$n" -ge "$#" ] && { echo "$s"; exit 0; }
  sleep 30
done
echo "TIMEOUT"; echo "$s"
