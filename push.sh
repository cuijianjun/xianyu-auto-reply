#!/bin/bash
git add .
git commit -m "$1"
default="master"
#d=`git symbolic-ref HEAD 2>/dev/null | cut -d"/" -f 3`
#echo $d;
targetBranch=$2
branch=${targetBranch-$default}
git push origin $branch
