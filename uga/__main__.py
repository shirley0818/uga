#!/usr/bin/env python

## Copyright (c) 2015 Ryan Koesterer GNU General Public License v3
##
##    This program is free software: you can redistribute it and/or modify
##    it under the terms of the GNU General Public License as published by
##    the Free Software Foundation, either version 3 of the License, or
##    (at your option) any later version.
##
##    This program is distributed in the hope that it will be useful,
##    but WITHOUT ANY WARRANTY; without even the implied warranty of
##    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##    GNU General Public License for more details.
##
##    You should have received a copy of the GNU General Public License
##    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import numpy as np
import pandas as pd
from collections import OrderedDict
import glob
from ConfigParser import SafeConfigParser
from pkg_resources import resource_filename
import signal
import subprocess
import shutil
import Parse
import Process
import Map
import Fxns
import pickle
from Bio import bgzf

def main(args=None):
	rerun = []
	args = Parse.get_args(Parse.get_parser())

	if args.which in ['snv','snvgroup','meta','resubmit']:
		if args.which == 'resubmit':
			with open(args.dir + '/' + os.path.basename(args.dir) + '.args.pkl', 'rb') as p:
				qsub = args.qsub if args.qsub else None
				args,cfg = pickle.load(p)
				if qsub:
					cfg['qsub'] = qsub
			with open(cfg['out'] + '/' + os.path.basename(cfg['out']) + '.rerun.pkl', 'rb') as p:
				rerun = pickle.load(p)
			os.remove(cfg['out'] + '/' + os.path.basename(cfg['out']) + '.rerun.pkl')
			cfg['replace'] = True
		else:
			cfg = getattr(Parse, 'generate_' + args.which + '_cfg')(args.ordered_args)
	else:
		cfg = getattr(Parse, 'generate_' + args.which + '_cfg')(args.ordered_args)

	##### read settings file #####
	ini = SafeConfigParser()
	ini.read(resource_filename('uga', 'settings.ini'))

	##### distribute jobs #####
	if args.which in ['snv','snvgroup','meta']:
		run_type = 0
		if cfg['cpus'] is not None and cfg['cpus'] > 1:
			run_type = run_type + 1
		if cfg['split']:
			run_type = run_type + 10
		if cfg['split_n']:
			run_type = run_type + 100

		if args.which == 'snv':
			#	generate regions dataframe with M rows, either from --snv-map or by splitting data file or --snv-region according to --mb
			#	run_type = 0:   run as single job
			#	run_type = 1:   --cpus C (distribute M regions over C cpus and run single job, 1 job C cpus)
			#	run_type = 10:  --split (split M regions into single region jobs, M jobs 1 cpu)
			#	run_type = 100: --split-n N (distribute M regions over N jobs, N jobs 1 cpu)
			#	run_type = 11:  --split, --cpus C (split M regions into chunks of size M / C and run M jobs, M jobs C cpus)
			#	run_type = 101: --split-n N, --cpus C (distribute M regions over N jobs and distribute each over C cpus, N jobs C cpus)

			if cfg['region_file']:
				regions_df = pd.read_table(cfg['region_file'],header=None,names=['region'], compression='gzip' if cfg['region_file'].split('.')[-1] == 'gz' else None)
				regions_df['chr'] = [int(x.split(':')[0]) for x in regions_df['region']]
				regions_df['start'] = [int(x.split(':')[1].split('-')[0]) for x in regions_df['region']]
				regions_df['end'] = [int(x.split(':')[1].split('-')[1]) for x in regions_df['region']]
				regions_df['job'] = 1
				regions_df['cpu'] = 1
			else:
				snv_map = []
				data_files = []
				for m in cfg['models']:
					if cfg['models'][m]['file'] not in data_files:
						snv_map.extend(Map.map(out=cfg['out'] + '.' + m + '.regions', file=cfg['models'][m]['file'], mb = cfg['mb'], region = cfg['region']))
						data_files.append(cfg['models'][m]['file'])
				snv_map = list(set(snv_map))
				regions_df = pd.DataFrame({'region': snv_map, 'chr': [int(x.split(':')[0]) for x in snv_map], 'start': [int(x.split(':')[1].split('-')[0]) for x in snv_map], 'end': [int(x.split(':')[1].split('-')[1]) for x in snv_map]})
				regions_df['job'] = 1
				regions_df['cpu'] = 1
				del data_files
				del snv_map
			regions_df = regions_df[['chr','start','end','region','job','cpu']]
			regions_df.sort_values(by=['chr','start'],inplace=True)
			regions_df.reset_index(drop=True,inplace=True)

		if args.which == 'meta':
			#	generate regions dataframe with M rows, either from --snv-map or by splitting data file or --snv-region according to --mb
			#	run_type = 0:   run as single job
			#	run_type = 1:   --cpus C (distribute M regions over C cpus and run single job, 1 job C cpus)
			#	run_type = 10:  --split (split M regions into single region jobs, M jobs 1 cpu)
			#	run_type = 100: --split-n N (distribute M regions over N jobs, N jobs 1 cpu)
			#	run_type = 11:  --split, --cpus C (split M regions into chunks of size M / C and run M jobs, M jobs C cpus)
			#	run_type = 101: --split-n N, --cpus C (distribute M regions over N jobs and distribute each over C cpus, N jobs C cpus)
			if cfg['region_file']:
				regions_df = pd.read_table(cfg['region_file'],header=None,names=['region'], compression='gzip' if cfg['region_file'].split('.')[-1] == 'gz' else None)
				regions_df['chr'] = [int(x.split(':')[0]) for x in regions_df['region']]
				regions_df['start'] = [int(x.split(':')[1].split('-')[0]) for x in regions_df['region']]
				regions_df['end'] = [int(x.split(':')[1].split('-')[1]) for x in regions_df['region']]
				regions_df['job'] = 1
				regions_df['cpu'] = 1
			else:
				snv_map = []
				data_files = []
				for f in cfg['files']:
					if f not in data_files:
						snv_map.extend(Map.map(out=cfg['out'] + '.' + f + '.regions', file=cfg['files'][f], mb = cfg['mb'], region = cfg['region']))
						data_files.append(cfg['files'][f])
				snv_map = list(set(snv_map))
				regions_df = pd.DataFrame({'region': snv_map, 'chr': [int(x.split(':')[0]) for x in snv_map], 'start': [int(x.split(':')[1].split('-')[0]) for x in snv_map], 'end': [int(x.split(':')[1].split('-')[1]) for x in snv_map]})
				regions_df['job'] = 1
				regions_df['cpu'] = 1
				del data_files
				del snv_map
			regions_df = regions_df[['chr','start','end','region','job','cpu']]
			regions_df.sort_values(by=['chr','start'],inplace=True)
			regions_df.reset_index(drop=True,inplace=True)

		if args.which == 'snvgroup':
			#	generate regions dataframe with M rows from --snvgroup-map
			#	run_type = 0:   run as single job
			#	run_type = 1:   --cpus C (distribute M snvgroups over C cpus and run single job, 1 job C cpus)
			#	run_type = 10:  --split (split M snvgroups into single region jobs, M jobs 1 cpu)
			#	run_type = 100: --split-n N (distribute M snvgroups over N jobs, N jobs 1 cpu)
			#	run_type = 101: --split-n N, --cpus C (distribute M snvgroups over N jobs and distribute each job over C cpus, N jobs C cpus)

			if cfg['region_file']:
				regions_df = pd.read_table(cfg['region_file'],header=None,names=['region','group_id'], compression='gzip' if cfg['region_file'].split('.')[-1] == 'gz' else None)
				regions_df['chr'] = [int(x.split(':')[0]) for x in regions_df['region']]
				regions_df['start'] = [int(x.split(':')[1].split('-')[0]) for x in regions_df['region']]
				regions_df['end'] = [int(x.split(':')[1].split('-')[1]) for x in regions_df['region']]
				regions_df['job'] = 1
				regions_df['cpu'] = 1
				regions_df = regions_df[['chr','start','end','region','group_id','job','cpu']]
				regions_df.sort_values(by=['chr','start'],inplace=True)
				regions_df.reset_index(drop=True,inplace=True)
			elif cfg['region']:
				snv_map = []
				data_files = []
				for m in cfg['models']:
					if cfg['models'][m]['file'] not in data_files:
						snv_map.extend(Map.map(out=cfg['out'] + '.' + m + '.regions', file=cfg['models'][m]['file'], mb = 1000, region = cfg['region']))
						data_files.append(cfg['models'][m]['file'])
				snv_map = list(set(snv_map))
				regions_df = pd.DataFrame({'region': snv_map, 'chr': [int(x.split(':')[0]) for x in snv_map], 'start': [int(x.split(':')[1].split('-')[0]) for x in snv_map], 'end': [int(x.split(':')[1].split('-')[1]) for x in snv_map]})
				regions_df['group_id'] = cfg['region']
				regions_df['job'] = 1
				regions_df['cpu'] = 1
				del data_files
				del snv_map
				regions_df = regions_df[['chr','start','end','region','group_id','job','cpu']]
				regions_df.sort_values(by=['chr','start'],inplace=True)
				regions_df.reset_index(drop=True,inplace=True)
			else:
				if cfg['snvgroup_map']:
					snvgroup_map = pd.read_table(cfg['snvgroup_map'],header=None,names=['chr','pos','marker','group_id'], compression='gzip' if cfg['snvgroup_map'].split('.')[-1] == 'gz' else None)
					regions_df = snvgroup_map[['chr','pos','group_id']]
					regions_df=regions_df.groupby(['chr','group_id'])
					regions_df = regions_df.agg({'pos': [np.min,np.max]})
					regions_df.columns = ['start','end']
					regions_df['chr'] = regions_df.index.get_level_values('chr')
					regions_df['group_id'] = regions_df.index.get_level_values('group_id')
					regions_df['region'] = regions_df.chr.map(str) + ':' + regions_df.start.map(str) + '-' + regions_df.end.map(str)
					regions_df['job'] = 1
					regions_df['cpu'] = 1
					regions_df = regions_df[['chr','start','end','region','group_id','job','cpu']]
					regions_df.drop_duplicates(inplace=True)
					regions_df.sort_values(by=['chr','start'],inplace=True)
					regions_df.reset_index(drop=True,inplace=True)

		if run_type == 1:
			n = int(np.ceil(regions_df.shape[0] / float(cfg['cpus'])))
			n_remain = int(regions_df.shape[0] - (n-1) * cfg['cpus'])
			regions_df['cpu'] = np.append(np.repeat(range(cfg['cpus'])[:n_remain],n),np.repeat(range(cfg['cpus'])[n_remain:],n-1)) + 1
		elif run_type == 10:
			regions_df['job'] = regions_df.index.values + 1
		elif run_type == 100:
			n = int(np.ceil(regions_df.shape[0] / float(cfg['split_n'])))
			n_remain = int(regions_df.shape[0] - (n-1) * cfg['split_n'])
			regions_df['job'] = np.append(np.repeat(range(cfg['split_n'])[:n_remain],n),np.repeat(range(cfg['split_n'])[n_remain:],n-1)) + 1
		elif run_type == 11 and args.which != 'snvgroup':
			cfg['split_n'] = int(np.ceil(regions_df.shape[0] / float(cfg['cpus'])))
			n = int(np.ceil(regions_df.shape[0] / float(cfg['split_n'])))
			n_remain = int(regions_df.shape[0] - (n-1) * cfg['split_n'])
			regions_df['job'] = np.append(np.repeat(range(cfg['split_n'])[:n_remain],n),np.repeat(range(cfg['split_n'])[n_remain:],n-1)) + 1
			for i in range(1,int(max(regions_df['job'])) + 1):
				n = int(np.ceil(regions_df[regions_df['job'] == i].shape[0] / float(cfg['cpus'])))
				n_remain = int(regions_df[regions_df['job'] == i].shape[0] - (n-1) * cfg['cpus'])
				regions_df.loc[regions_df['job'] == i,'cpu'] = np.append(np.repeat(range(cfg['cpus'])[:n_remain],n),np.repeat(range(cfg['cpus'])[n_remain:],n-1)) + 1
			cfg['split'] = None
		elif run_type == 101:
			n = int(np.ceil(regions_df.shape[0] / float(cfg['split_n'])))
			n_remain = int(regions_df.shape[0] - (n-1) * cfg['split_n'])
			regions_df['job'] = np.append(np.repeat(range(cfg['split_n'])[:n_remain],n),np.repeat(range(cfg['split_n'])[n_remain:],n-1)) + 1
			for i in range(1,int(max(regions_df['job'])) + 1):
				n = int(np.ceil(regions_df[regions_df['job'] == i].shape[0] / float(cfg['cpus'])))
				n_remain = int(regions_df[regions_df['job'] == i].shape[0] - (n-1) * cfg['cpus'])
				regions_df.loc[regions_df['job'] == i,'cpu'] = np.append(np.repeat(range(cfg['cpus'])[:n_remain],n),np.repeat(range(cfg['cpus'])[n_remain:],n-1)) + 1
		if int(max(regions_df['job'])) + 1 > 100000:
			print Process.print_error('number of jobs exceeds 100,000, consider using --split-n to reduce the total number of jobs')
			return

	##### generate output directories #####
	directory = os.getcwd()

	if args.which in ['snv','snvgroup','meta']:
		print 'detected run type ' + str(run_type) + ' ...'
		if len(rerun) == 0:
			if int(max(regions_df['job'])) > 1 and cfg['qsub'] is not None:
				if 'mb' in cfg:
					print '   ' + str(regions_df.shape[0]) + ' regions of size ' + str(cfg['mb']) + 'mb detected'
				else:
					print '   ' + str(regions_df.shape[0]) + ' regions detected'
				print '   ' + str(int(max(regions_df['job']))) + ' jobs will be submitted'
				print '   <= ' + str(max(np.bincount(regions_df['job']))) + ' regions per job'
				print '   <= '  + str(int(max(regions_df['cpu']))) + ' cpus per job'
				print '   qsub options: ' + cfg['qsub']
				print '   output directory: ' + directory
				print '   replace: ' + str(cfg['replace'])
				input_var = None
				while input_var not in ['y','n','Y','N']:
					input_var = raw_input('\nsubmit jobs (yY/nN)? ')
				if input_var.lower() == 'n':
					print 'canceled by user'
					return

			directory = directory + '/' + os.path.basename(cfg['out'])
			if os.path.exists(directory):
				if args.replace:
					print 'replacing existing results'
					try:
						shutil.rmtree(directory)
					except OSError:
						print Process.print_error('unable to replace results directory' + directory)
				else:
					print Process.print_error('results directory ' + directory + ' already exists, use --replace to overwrite existing results')
					return
			try:
				os.mkdir(directory)
			except OSError:
				pass

			with open(directory + '/' + os.path.basename(cfg['out']) + '.args.pkl', 'wb') as p:
				pickle.dump([args, cfg], p)

			if run_type in [10,11,100,101] and regions_df.shape[0] > 1:
				for j in range(1, int(max(regions_df['job'])) + 1):
					try:
						os.mkdir(directory + '/jobs' + str(100 * ((j-1) / 100) + 1) + '-' + str(100 * ((j-1) / 100) + 100))
					except OSError:
						pass
					try:
						os.mkdir(directory + '/jobs' + str(100 * ((j-1) / 100) + 1) + '-' + str(100 * ((j-1) / 100) + 100) + '/job' + str(j))
					except OSError:
						pass
				with open(directory + '/' + cfg['out'] + '.files', 'w') as jlist:
					for j in range(1, int(max(regions_df['job'])) + 1):
						if args.which in ['snv','snvgroup']:
							if 'model_order' in cfg:
								for m in cfg['model_order']:
									jlist.write(str(j) + '\t' + cfg['out'] + '.' + m + '.gz' + '\t' + 'jobs' + str(100 * ((j-1) / 100) + 1) + '-' + str(100 * ((j-1) / 100) + 100) + '/job' + str(j) + '/' + cfg['out'] + '.job' + str(j) + '.' + m + '.gz\n')
							else:
								jlist.write(str(j) + '\t' + cfg['out'] + '.gz' + '\t' + 'jobs' + str(100 * ((j-1) / 100) + 1) + '-' + str(100 * ((j-1) / 100) + 100) + '/job' + str(j) + '/' + cfg['out'] + '.job' + str(j) + '.gz\n')
						if 'meta_order' in cfg:
							if len(cfg['meta_order']) > 0:
								for m in cfg['meta_order']:
									jlist.write(str(j) + '\t' + cfg['out'] + '.' + m + '.gz' + '\t' + 'jobs' + str(100 * ((j-1) / 100) + 1) + '-' + str(100 * ((j-1) / 100) + 100) + '/job' + str(j) + '/' + cfg['out'] + '.job' + str(j) + '.' + m + '.gz\n')
		else:
			directory = directory + '/' + os.path.basename(cfg['out'])
			if int(max(regions_df['job'])) > 1 and cfg['qsub'] is not None:
				print 'detected resubmit ...'
				print '   ' + str(len(rerun)) + ' jobs will be submitted'
				print '   <= ' + str(max(np.bincount(regions_df['job']))) + ' regions per job'
				print '   <= '  + str(int(max(regions_df['cpu']))) + ' cpus per job'
				print '   qsub options: ' + cfg['qsub']
				print '   output directory: ' + directory
				print '   replace: ' + str(cfg['replace'])
				input_var = None
				while input_var not in ['y','n','Y','N']:
					input_var = raw_input('\nresubmit jobs (yY/nN)? ')
				if input_var.lower() == 'n':
					print 'canceled by user'
					return

	##### locate qsub wrapper #####
	qsub_wrapper = resource_filename('uga', 'Qsub.py')

	if args.which == 'set':
		if 'ordered_args' in args:
			for k in args.ordered_args:
				ini.set('main',k[0],k[1])
			with open(resource_filename('uga', 'settings.ini'), 'w') as f:
				ini.write(f)
		print 'main settings ...'
		for s in ini.sections():
			for k in ini.options(s):
				print '   ' + k + ' = ' + ini.get(s,k)

	elif args.which in ['snv','snvgroup','meta','resubmit']:
		if cfg['qsub']:
			print "submitting jobs\n"
		out = cfg['out']
		joblist = range(1, int(max(regions_df['job'])) + 1) if len(rerun) == 0 else rerun
		for j in joblist:
			regions_job_df = regions_df[regions_df['job'] == j].reset_index(drop=True)
			if int(max(regions_df['job'])) > 1:
				cfg['out'] = directory + '/jobs' + str(100 * ((j-1) / 100) + 1) + '-' + str(100 * ((j-1) / 100) + 100) + '/job' + str(j) + '/' + out + '.job' + str(j)
				regions_job_df.to_csv(cfg['out'] + '.regions', index = False, header = True, sep='\t', na_rep='None')
			else:
				cfg['out'] = directory + '/' + out
				regions_job_df.to_csv(cfg['out'] + '.regions', index = False, header = True, sep='\t', na_rep='None')
			args.ordered_args = [('out',cfg['out']),('region_file',cfg['out'] + '.regions'),('cpus',int(max(regions_job_df['cpu'])))] + [x for x in args.ordered_args if x[0] not in ['out','region_file','cpus']]
			cmd = 'Run' + args.which.capitalize() + '(' + str(args.ordered_args) + ')'
			if cfg['qsub']:
				Process.qsub(['qsub'] + cfg['qsub'].split() + ['-o',cfg['out'] + '.' + args.which + '.log',qsub_wrapper],'\"' + cmd + '\"')
			else:
				Process.interactive(qsub_wrapper, cmd, cfg['out'] + '.' + args.which + '.log')

	elif args.which == 'compile':
		files = pd.read_table(args.dir + '/' + os.path.basename(args.dir) + '.files', names=['job','out','file'])
		complete, rerun = Fxns.verify_results(args.dir,files)
		if len(rerun) > 0:
			print Process.print_error('detected ' + str(len(rerun)) + ' failed jobs\n       use resubmit module to rerun failed jobs')
			with open(args.dir + '/' + os.path.basename(args.dir) + '.rerun.pkl', 'wb') as p:
				pickle.dump(rerun, p)
		else:
			complete = Fxns.compile_results(args.dir,files)
			if complete:
				input_var = None
				while input_var not in ['y','n','Y','N']:
					input_var = raw_input('delete obselete job subdirectories for this project (yY/nN)? ')
				if input_var.lower() == 'n':
					print 'canceled by user'
				else:
					print 'deleting subdirectories'
					for d in glob.glob(args.dir + '/jobs*-*'):
						try:
							shutil.rmtree(d)
						except OSError:
							print Process.print_error('unable to delete job data directory ' + d)
			else:
				print Process.print_error('file compilation incomplete')

	elif args.which in ['snvgroupplot','snvplot']:
		cfg['out'] = '.'.join(cfg['file'].split('.')[0:len(cfg['file'].split('.'))-1]) + '.' + args.which
		args.ordered_args = [('out',cfg['out'])] + [x for x in args.ordered_args if x[0] not in ['out']]
		cmd = 'Run' + args.which.capitalize() + '(' + str(args.ordered_args) + ')'
		if cfg['qsub'] is not None:
			Process.qsub(['qsub'] + cfg['qsub'].split() + ['-o',cfg['out'] + '.log',qsub_wrapper],'\"' + cmd + '\"')
		else:
			Process.interactive(qsub_wrapper, cmd, cfg['out'] + '.log')

	elif args.which == 'filter':
		if os.path.exists(cfg['file'].replace('.gz','.' + cfg['tag'] + '.log')):
			if args.replace:
				try:
					os.remove(cfg['file'].replace('.gz','.' + cfg['tag'] + '.log'))
				except OSError:
					print Process.print_error('unable to remove existing log file ' + cfg['file'].replace('.gz','.' + cfg['tag'] + '.log'))
					return
			else:
				print Process.print_error('log file ' + cfg['file'].replace('.gz','.' + cfg['tag'] + '.log') + ' already exists, use --replace to overwrite existing results')
				return
		if os.path.exists(cfg['file'].replace('.gz','.' + cfg['tag'] + '.gz')):
			if args.replace:
				try:
					os.remove(cfg['file'].replace('.gz','.' + cfg['tag'] + '.gz'))
				except OSError:
					print Process.print_error('unable to remove existing inflation corrected results file ' + cfg['file'].replace('.gz','.' + cfg['tag'] + '.gz'))
			else:
				print Process.print_error('results file ' + cfg['file'].replace('.gz','.' + cfg['tag'] + '.gz') + ' already exists, use --replace to overwrite existing results')
				return
		if os.path.exists(cfg['file'].replace('.gz','.' + cfg['tag'] + '.gz.tbi')):
			if args.replace:
				try:
					os.remove(cfg['file'].replace('.gz','.' + cfg['tag'] + '.gz.tbi'))
				except OSError:
					print Process.print_error('unable to remove existing inflation corrected results index file ' + cfg['file'].replace('.gz','.' + cfg['tag'] + '.gz.tbi'))
			else:
				print Process.print_error('results index file ' + cfg['file'].replace('.gz','.' + cfg['tag'] + '.gz.tbi') + ' already exists, use --replace to overwrite existing results')
				return
		cmd = 'Run' + args.which.capitalize() + '(' + str(args.ordered_args) + ')'
		if cfg['qsub'] is not None:
			Process.qsub(['qsub'] + cfg['qsub'].split() + ['-o',cfg['file'].replace('.gz','.' + cfg['tag'] + '.log'),qsub_wrapper],'\"' + cmd + '\"')
		else:
			Process.interactive(qsub_wrapper, cmd, cfg['file'].replace('.gz','.' + cfg['tag'] + '.log'))

	else:
		print Process.print_error(args.which + " not a currently available module")

	print ''

if __name__ == "__main__":
	main()
	os._exit(0)

