#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p "python3.withPackages(ps: [ ps.matplotlib ])"

import json
import gzip
import os
import shutil
import sys
import time
import urllib.request

# Graphing
import matplotlib
import matplotlib.pyplot as plt

params = {
	 8: { 'step': 1 },
	16: { 'step': 2 },
}

refresh_period_hours = 23

data_file = "./minipools.json.gz"

def file_age_hours(f):
	age_seconds = time.time() - os.path.getmtime(data_file)
	return age_seconds / 60 / 60

if not os.path.exists(data_file) or file_age_hours(data_file) > refresh_period_hours:
	print("Retrieving minipool data", file=sys.stderr)
	headers = { 'Accept-Encoding': 'gzip' }
	req = urllib.request.Request('https://rocketscan.io/api/mainnet/minipools/all', headers=headers)
	with urllib.request.urlopen(req) as response, open(data_file, 'wb') as out_file:
	    shutil.copyfileobj(response, out_file)

with gzip.open(data_file, 'r') as f:
	data = json.load(f)

collateralizations = {
	 8: [0] * (1 +  50 // params[8]['step']),
	16: [0] * (1 + 150 // params[16]['step']),
}

for minipool in data:
	#print(minipool, file=sys.stderr)
	leb = int(minipool['nodeDepositBalance']) // 10**18
	node = minipool['node']
	stake = int(node['rplStake'])
	min_stake = int(node['rplMinStake'])
	if min_stake == 0: continue
	collat = stake/min_stake * 10 / 100
	borrowed = 32 - leb
	collat = min(collat, 1.5 * leb / borrowed)
	collat_perc = int(100*collat / params[leb]['step'])
	collateralizations[leb][collat_perc] += borrowed

for kind in [8, 16]:
	collateralization = collateralizations[kind]
	step = params[kind]['step']
	
	x=[]
	y=[]
	# Create the figure and axes objects, specify the size and the dots per inches
	fig, ax = plt.subplots(figsize=(15, 4))
	start = min([coll for coll, count in enumerate(collateralization) if count > 0])
	for coll, count in list(enumerate(collateralization))[start:]:
		x.append(step * coll)
		y.append(count)
	
	ax.bar(x, y, width=step, zorder=2)
	
	ax.grid(which="major", axis='x', color='#DAD8D7', alpha=0.5, zorder=1)
	ax.grid(which="major", axis='y', color='#DAD8D7', alpha=0.5, zorder=1)
	
	plt.xlabel("Staked RPL vs borrowed ETH")
	
	# Add a '+' to the last ticker, e.g. "50%+" as the last ticker for LEB8, since it aggregates all levels above
	@matplotlib.ticker.FuncFormatter
	def major_formatter(tick, pos):
		res = f'{tick:.0f}%'
		if tick == x[-1]:
			res += '+'
		return res
	ax.xaxis.set_major_formatter(major_formatter)
	
	ax.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(base=5 * step))
	
	plt.ylabel("Borrowed ETH")
	ax.yaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter('Ξ{x:,.0f}'))
	
	plt.title(f"{kind} ETH Minipools", fontsize=14, weight='bold', alpha=.8)
	plt.savefig(f"../harpocryptes.github.io/minipools-{kind}eth.svg")
