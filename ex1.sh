#!/bin/bash
x=1
until [ $x -gt 3 ]; do
  echo "x is $x"
  ((x++))
done
