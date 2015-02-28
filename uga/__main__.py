#!/usr/bin/env python

import os
import gzip
import sys
import string
import math
import time
import subprocess
import os.path
import numpy as np
import pandas as pd
import re
from Messages import Error
from File import RemoveExistingFiles,CheckExistingFiles,PrepareChrDirs,PrepareListDirs,GenerateSubFiles,CheckResults,CompileResults
from Cfg import Cfg
from Coordinates import Coordinates
from Process import Qsub,Interactive
from Parse import Parse,Parser
from __init__ import __version__

def main(args=None):
	parser=Parser()
	args=Parse(parser)

	##### read cfg file into dictionary #####
	if args.which == 'meta':
		print "reading configuration from file"
		config = Cfg(args.cfg, args.which, args.vars).Load()
		args.out = config['out']

	##### define region list #####
	if args.which in ['model','meta','summary']:
		n = 1
		dist_mode = 'full'
		print "generating list of genomic regions ...", 
		if args.region_list:
			region_df = Coordinates(args.region_list).Load()
			if args.split or args.split_n:
				if not args.split_n or args.split_n > len(region_df.index):
					n = len(region_df.index)
					dist_mode = 'split-list'
				else:
					n = args.split_n
					dist_mode = 'split-list-n'
			else:
				dist_mode = 'list'
		elif args.region:
			if len(args.region.split(':')) > 1:
				region_df = pd.DataFrame({'chr': [re.split(':|-', args.region)[0]], 'start': [re.split(':|-', args.region)[1]], 'end': [re.split(':|-', args.region)[2]], 'region': [args.region]})
				dist_mode = 'region'
			else:
				region_df = pd.DataFrame({'chr': [args.region],'start': ['NA'],'end': ['NA'],'region': [args.region]})
				dist_mode = 'chr'
			n = 1
		else:
			region_df = pd.DataFrame({'chr': [str(i+1) for i in range(26)],'start': ['NA' for i in range(26)],'end': ['NA' for i in range(26)],'region': [str(i+1) for i in range(26)]})
			n = 1
		print " " + str(len(region_df.index)) + " regions found"

		##### get job list from file #####
		if args.job_list:
			jobs = []
			with open(args.job_list) as f:
				lines = (line.rstrip() for line in f)
				lines = (line for line in lines if line)
				for line in lines:
					jobs.append(int(line))
			print "" + str(len(jobs)) + " jobs read from job list file"

		##### define output directory and update out file name #####
		directory = os.path.dirname(args.out) if not args.directory else args.directory
		directory = directory + '/' if args.directory else directory
		if n > 1:
			if dist_mode == 'split-list':
				directory = directory + 'chr[CHR]/'
			elif dist_mode == 'split-list-n':
				directory = directory + 'list[LIST]/'
		if 'out' in vars(args).keys():
			args.out = directory + args.out
	
		##### generate out file names for split jobs or chr/region specific jobs #####
		out_files = {}
		if dist_mode in ['chr','region','split-list','split-list-n']:
			out_files = GenerateSubFiles(region_df = region_df, f = args.out, dist_mode = dist_mode, n = n)

	##### define script library path #####
	script_path = os.environ['UGA_BIN']

	if args.which == 'summary':
		summary_out = os.path.basename(args.out) if not args.out_rename else args.out_rename
		if args.verify:
			complete_string = 'process complete' if not args.complete_string else args.complete_string
			print "scanning for previous check results files"
			if os.path.exists(summary_out + '.verify' + '.files.incomplete'):
				if args.overwrite:
					os.remove(summary_out + '.verify' + '.files.incomplete')
				else:
					print Error("file " + summary_out + '.verify' + ".files.incomplete already exists (use --overwrite flag to replace the existing file)")
					sys.exit()
			if os.path.exists(summary_out + '.verify' + '.files.missing'):
				if args.overwrite:
					os.remove(summary_out + '.verify' + '.files.missing')
				else:
					print Error("file " + summary_out + '.verify' + ".files.missing already exists (use --overwrite flag to replace the existing file)")
					sys.exit()
			if os.path.exists(summary_out + '.verify' + '.regions.rerun'):
				if args.overwrite:
					os.remove(summary_out + '.verify' + '.regions.rerun')
				else:
					print Error("file " + summary_out + '.verify' + ".regions.rerun already exists (use --overwrite flag to replace the existing file)")
					sys.exit()
		if args.compile:
			print "scanning for previous compiled results files"
			if os.path.exists(summary_out + '.gz'):
				if args.overwrite:
					os.remove(summary_out + '.gz')
				else:
					print Error("file " + summary_out + ".gz already exists (use --overwrite flag to replace the existing file)")
					sys.exit()
			if os.path.exists(summary_out + '.gz.tbi'):
				if args.overwrite:
					os.remove(summary_out + '.gz.tbi')
				else:
					print Error("file " + summary_out + ".gz.tbi already exists (use --overwrite flag to replace the existing file)")
					sys.exit()
		if args.qq or args.manhattan:
			if args.overwrite:
				RemoveExistingFiles(summary_out, 'plot')
			else:
				CheckExistingFiles(summary_out, 'plot')
		if dist_mode in ['split-list', 'split-list-n'] and args.verify:
			if not CheckResults(out_files, summary_out + '.verify', args.cpu, complete_string, args.overwrite):
				print Error("results could not be verified")
				sys.exit()
		if dist_mode in ['split-list', 'split-list-n'] and len(out_files.keys()) > 1 and args.compile:
			if not CompileResults(out_files, summary_out, args.overwrite):
				print Error("results could not be compiled")
				sys.exit()
		if args.qq or args.manhattan:
			from Plot import Plot
			cmd = 'Plot(data="' + summary_out + '.gz",out="' + summary_out + '"'
			for x in ['ext','qq','manhattan','gc','chr','pos','p','rsq','freq','hwe','meta_dir','rsq_thresh','freq_thresh','hwe_thresh','df_thresh','sig','calc_sig']:
				if x in vars(args).keys() and not vars(args)[x] in [False,None]:
					if type(vars(args)[x]) is str:
						cmd = cmd + ',' + x + '="' + str(vars(args)[x]) + '"'
					else:
						cmd = cmd + ',' + x + '=' + str(vars(args)[x])
			cmd = cmd + ')'
			Interactive('quga', cmd, summary_out + '.plot.log')
	elif args.which in ['model','meta']:
		if not os.path.exists(args.directory):
			try:
				os.mkdir(args.directory)
			except OSError:
				print Error("unable to create output directory")
				sys.exit()
		print "preparing output directories"
		if dist_mode == 'split-list' and n > 1:
			PrepareChrDirs(region_df['region'], directory)
		elif dist_mode == 'split-list-n' and n > 1:
			PrepareListDirs(n, directory)
		if args.qsub:
			print "submitting jobs\n"
		joblist = []
		if not args.job is None:
			joblist.append(args.job)
		elif not args.job_list is None:
			joblist.extend(jobs)
		else:
			joblist.extend(range(n))
		name = args.which + '.' + os.path.basename(args.out) if not args.name else args.name
		for i in joblist:
			if dist_mode in ['split-list', 'region']:
				out = out_files['%s:%s-%s' % (str(region_df['chr'][i]), str(region_df['start'][i]), str(region_df['end'][i]))]
				if n > 1:
					vars(args)['region'] = '%s:%s-%s' % (str(region_df['chr'][i]), str(region_df['start'][i]), str(region_df['end'][i]))
					vars(args)['region_list'] = None
			elif dist_mode == 'split-list-n':
				out = out_files[i]
				rlist = out + '.regions'
				region_df.loc[np.array_split(np.array(region_df.index), n)[i]].to_csv(rlist, header=False, index=False, sep='\t', columns=['region', 'reg_id'])
				vars(args)['region_list'] = rlist
			elif dist_mode == 'chr':
				out = out_files['%s' % (str(region_df['chr'][i]))]
			else:
				out = args.out
			if args.overwrite:
				RemoveExistingFiles(out, args.which)
			else:
				CheckExistingFiles(out, args.which)
			if args.which == 'model':
				cmd = args.which.capitalize() + '(out=\'' + out + '\''
				for x in ['oxford','dos1','dos2','plink','vcf','samples','pheno','model','fid','iid','method','focus','sig','region_list','region','region_id','sex','male','female','buffer','corstr','miss','freq','rsq','hwe','case','ctrl','nofail','kinship','delimiter']:
					if x in vars(args).keys() and not str(vars(args)[x]) in ['False','None']:
						if x in ['oxford','dos1','dos2','plink','vcf']:
							cmd = cmd + ',data=\'' + str(vars(args)[x]) + '\',format=\'' + x + '\''
						elif type(vars(args)[x]) is str:
							cmd = cmd + ',' + x + '=\'' + str(vars(args)[x]) + '\''
						else:
							cmd = cmd + ',' + x + '=' + str(vars(args)[x])
				cmd = cmd + ',mem=' + str(args.mem) + ')'
			elif args.which == 'meta':
				config['out'] = out
				cmd = args.which.capitalize() + '(cfg=' + str(config)
				for x in ['region_list', 'region', 'method']:
					if x in vars(args).keys() and not vars(args)[x] in [False,None]:
						if type(vars(args)[x]) is str:
							cmd = cmd + ',' + x + '=\'' + str(vars(args)[x]) + '\''
						else:
							cmd = cmd + ',' + x + '=' + str(vars(args)[x])
				cmd = cmd + ',mem=' + str(args.mem) + ')'
			if args.qsub:
				Qsub('qsub -P ' + args.qsub + ' -l mem_free=' + str(args.mem) + 'g -N ' + name + ' -o ' + out + '.log ' + 'quga --internal --cmd \"' + cmd + '\"')
			else:
				Interactive('quga', cmd, out + '.log')
	elif args.which == 'map':
		if args.split_chr:
			for i in range(26):
				cmd = args.which.capitalize() + '(out=\'' + args.out + '.chr' + str(i+1) + '\',chr=' + str(i+1)
				for x in ['oxford','dos1','dos2','plink','vcf','b','kb','mb','n']:
					if x in vars(args).keys() and not vars(args)[x] in [False,None]:
						if type(vars(args)[x]) is str:
							cmd = cmd + ',' + x + '=\'' + str(vars(args)[x]) + '\''
						else:
							cmd = cmd + ',' + x + '=' + str(vars(args)[x])
				cmd = cmd + ')'
				if args.overwrite:
					RemoveExistingFiles(args.out + '.chr' + str(i+1), args.which)
				else:
					CheckExistingFiles(args.out + '.chr' + str(i+1), args.which)
				name = args.which + '.' + os.path.basename(args.out + '.chr' + str(i+1)) if not args.name else args.name
				if args.qsub:
					Qsub('qsub -P ' + args.qsub + ' -N ' + name + ' -o ' + args.out + '.chr' + str(i+1) + '.log ' + 'quga --internal --cmd \"' + cmd + '\"')
				else:
					Interactive('quga', cmd)
		else:
			cmd = args.which.capitalize() + '(out=\'' + args.out + '\''
			for x in ['oxford','dos1','dos2','plink','vcf','b','kb','mb','n','chr']:
				if x in vars(args).keys() and not vars(args)[x] in [False,None]:
					if type(vars(args)[x]) is str:
						cmd = cmd + ',' + x + '=\'' + str(vars(args)[x]) + '\''
					else:
						cmd = cmd + ',' + x + '=' + str(vars(args)[x])
			cmd = cmd + ')'
			if args.overwrite:
				RemoveExistingFiles(args.out, args.which)
			else:
				CheckExistingFiles(args.out, args.which)
			name = args.which + '.' + os.path.basename(args.out) if not args.name else args.name
			if args.qsub:
				Qsub('qsub -P ' + args.qsub + ' -N ' + name + ' -o ' + args.out + '.log ' + 'quga --internal --cmd \"' + cmd + '\"')
			else:
				Interactive('quga', cmd)
	else:
		print Error(args.which + " not a module")
	print ''

if __name__ == "__main__":
	main()
